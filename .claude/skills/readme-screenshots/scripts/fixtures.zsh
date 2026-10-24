#!/bin/zsh
# Creates the demo Go modules under ~/code and the demo zsh history.
set -euo pipefail

S=${0:A:h:h}
ROOT=$HOME/code

for tool in go git; do
	command -v $tool >/dev/null || { echo "fixtures: missing $tool"; exit 1 }
done
if [[ -e $ROOT ]]; then
	echo "fixtures: ~/code exists, refusing"
	exit 1
fi

COMMIT_N=0

# put <path>: write stdin to a file, creating parent dirs.
put() {
	mkdir -p ${1:h}
	cat > $1
}

# commit <message>: stage everything, commit 3 h after the previous one.
commit() {
	local d
	d=$(date -u -v+$((COMMIT_N * 3))H -j -f '%Y-%m-%dT%H:%M:%S' \
		'2026-10-19T09:00:00' '+%Y-%m-%dT%H:%M:%S+00:00')
	COMMIT_N=$((COMMIT_N + 1))
	git add -A
	GIT_AUTHOR_DATE=$d GIT_COMMITTER_DATE=$d \
		git -c user.name='Demo User' -c user.email=demo@example.com \
		-c commit.gpgsign=false commit -q -m "$1"
}

# scaffold <name>: repo, module, Makefile, .gitignore, README.
scaffold() {
	local name=$1
	mkdir -p $ROOT/$name
	cd $ROOT/$name
	COMMIT_N=0
	git init -q -b main
	go mod init example.com/$name 2>/dev/null
	put Makefile <<'EOF'
.PHONY: test lint

test:
	go test -count=1 ./...

lint:
	golangci-lint run
EOF
	printf '/bin/\n' | put .gitignore
	put README.md <<EOF
# $name

Demo service for screenshots. Stdlib only.
Run \`make test\` to check it.
EOF
}

# ---------------------------------------------------------------- orders-api
scaffold orders-api
commit 'chore: init module'

put internal/domain/order.go <<'EOF'
package domain

import (
	"errors"
	"time"
)

type Status string

const (
	StatusPending   Status = "pending"
	StatusPaid      Status = "paid"
	StatusCancelled Status = "cancelled"
)

var (
	ErrNotFound      = errors.New("order not found")
	ErrInvalidAmount = errors.New("amount must be positive")
)

type Order struct {
	ID          string    `json:"id"`
	CustomerID  string    `json:"customer_id"`
	AmountCents int64     `json:"amount_cents"`
	Currency    string    `json:"currency"`
	Status      Status    `json:"status"`
	CreatedAt   time.Time `json:"created_at"`
}
EOF
commit 'feat(domain): add order model and errors'

put internal/usecase/orders.go <<'EOF'
package usecase

import (
	"context"
	"errors"
	"fmt"
	"time"

	"example.com/orders-api/internal/domain"
)

type Repository interface {
	Save(ctx context.Context, key string, o domain.Order) error
	Get(ctx context.Context, id string) (domain.Order, error)
	GetByIdempotencyKey(ctx context.Context, key string) (domain.Order, error)
}

type CreateInput struct {
	CustomerID     string
	AmountCents    int64
	Currency       string
	IdempotencyKey string
}

type Orders struct {
	repo  Repository
	now   func() time.Time
	newID func() string
}

func NewOrders(repo Repository, now func() time.Time, newID func() string) *Orders {
	return &Orders{repo: repo, now: now, newID: newID}
}

func (u *Orders) Create(ctx context.Context, in CreateInput) (domain.Order, error) {
	if in.AmountCents <= 0 {
		return domain.Order{}, fmt.Errorf("create order: %w", domain.ErrInvalidAmount)
	}
	// A retried request must return the first order, not create a second one.
	if in.IdempotencyKey != "" {
		o, err := u.repo.GetByIdempotencyKey(ctx, in.IdempotencyKey)
		if err == nil {
			return o, nil
		}
		if !errors.Is(err, domain.ErrNotFound) {
			return domain.Order{}, fmt.Errorf("create order: lookup key: %w", err)
		}
	}
	o := domain.Order{
		ID:          u.newID(),
		CustomerID:  in.CustomerID,
		AmountCents: in.AmountCents,
		Currency:    in.Currency,
		Status:      domain.StatusPending,
		CreatedAt:   u.now(),
	}
	if err := u.repo.Save(ctx, in.IdempotencyKey, o); err != nil {
		return domain.Order{}, fmt.Errorf("create order: save: %w", err)
	}
	return o, nil
}

func (u *Orders) Get(ctx context.Context, id string) (domain.Order, error) {
	o, err := u.repo.Get(ctx, id)
	if err != nil {
		return domain.Order{}, fmt.Errorf("get order %s: %w", id, err)
	}
	return o, nil
}
EOF
put internal/repository/memory.go <<'EOF'
package repository

import (
	"context"
	"sync"

	"example.com/orders-api/internal/domain"
)

type Memory struct {
	mu     sync.RWMutex
	orders map[string]domain.Order
	keys   map[string]string
}

func NewMemory() *Memory {
	return &Memory{
		orders: make(map[string]domain.Order),
		keys:   make(map[string]string),
	}
}

func (m *Memory) Save(_ context.Context, key string, o domain.Order) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.orders[o.ID] = o
	if key != "" {
		m.keys[key] = o.ID
	}
	return nil
}

func (m *Memory) Get(_ context.Context, id string) (domain.Order, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	o, ok := m.orders[id]
	if !ok {
		return domain.Order{}, domain.ErrNotFound
	}
	return o, nil
}

func (m *Memory) GetByIdempotencyKey(
	_ context.Context,
	key string,
) (domain.Order, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	id, ok := m.keys[key]
	if !ok {
		return domain.Order{}, domain.ErrNotFound
	}
	return m.orders[id], nil
}
EOF
commit 'feat(usecase): create and fetch orders'

put internal/handler/orders.go <<'EOF'
package handler

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"

	"example.com/orders-api/internal/domain"
	"example.com/orders-api/internal/usecase"
)

var errBadJSON = errors.New("bad json")

type OrderService interface {
	Create(
		ctx context.Context,
		in usecase.CreateInput,
	) (domain.Order, error)
	Get(ctx context.Context, id string) (domain.Order, error)
}

type Orders struct {
	svc OrderService
}

func NewOrders(svc OrderService) *Orders {
	return &Orders{svc: svc}
}

func (h *Orders) Routes(mux *http.ServeMux) {
	mux.HandleFunc("POST /orders", h.create)
	mux.HandleFunc("GET /orders/{id}", h.get)
}

type createRequest struct {
	CustomerID  string `json:"customer_id"`
	AmountCents int64  `json:"amount_cents"`
	Currency    string `json:"currency"`
}

func (h *Orders) create(w http.ResponseWriter, r *http.Request) {
	var req createRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, errBadJSON)
		return
	}
	order, err := h.svc.Create(r.Context(), usecase.CreateInput{
		CustomerID:  req.CustomerID,
		AmountCents: req.AmountCents,
		Currency:    req.Currency,
	})
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, order)
}

func (h *Orders) get(w http.ResponseWriter, r *http.Request) {
	order, err := h.svc.Get(r.Context(), r.PathValue("id"))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, order)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, err error) {
	status := http.StatusInternalServerError
	switch {
	case errors.Is(err, errBadJSON):
		status = http.StatusBadRequest
	case errors.Is(err, domain.ErrNotFound):
		status = http.StatusNotFound
	case errors.Is(err, domain.ErrInvalidAmount):
		status = http.StatusUnprocessableEntity
	}
	body := map[string]string{"error": http.StatusText(status)}
	writeJSON(w, status, body)
}
EOF
commit 'feat(handler): expose orders over HTTP'

put internal/handler/orders_test.go <<'EOF'
package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"example.com/orders-api/internal/domain"
	"example.com/orders-api/internal/usecase"
)

type fakeService struct {
	order domain.Order
	err   error
}

func (f fakeService) Create(
	_ context.Context,
	_ usecase.CreateInput,
) (domain.Order, error) {
	return f.order, f.err
}

func (f fakeService) Get(
	_ context.Context,
	_ string,
) (domain.Order, error) {
	return f.order, f.err
}

func TestOrdersCreate(t *testing.T) {
	order := domain.Order{
		ID:          "ord_1",
		AmountCents: 1250,
		Currency:    "EUR",
		Status:      domain.StatusPending,
		CreatedAt:   time.Unix(1792400000, 0),
	}
	tests := []struct {
		name string
		body string
		svc  fakeService
		want int
	}{
		{
			name: "created",
			body: `{"customer_id":"c1","amount_cents":1250}`,
			svc:  fakeService{order: order},
			want: http.StatusCreated,
		},
		{
			name: "invalid amount",
			body: `{"customer_id":"c1","amount_cents":0}`,
			svc:  fakeService{err: domain.ErrInvalidAmount},
			want: http.StatusUnprocessableEntity,
		},
		{
			name: "bad json",
			body: `{"customer_id":`,
			svc:  fakeService{order: order},
			want: http.StatusBadRequest,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mux := http.NewServeMux()
			NewOrders(tt.svc).Routes(mux)
			req := httptest.NewRequest(
				http.MethodPost,
				"/orders",
				strings.NewReader(tt.body),
			)
			rec := httptest.NewRecorder()
			mux.ServeHTTP(rec, req)
			if rec.Code != tt.want {
				t.Fatalf("status = %d, want %d", rec.Code, tt.want)
			}
		})
	}
}
EOF
put cmd/orders-api/main.go <<'EOF'
package main

import (
	"crypto/rand"
	"encoding/hex"
	"log"
	"net/http"
	"time"

	"example.com/orders-api/internal/handler"
	"example.com/orders-api/internal/repository"
	"example.com/orders-api/internal/usecase"
)

func newID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return "ord_" + hex.EncodeToString(b)
}

func main() {
	repo := repository.NewMemory()
	svc := usecase.NewOrders(repo, time.Now, newID)
	mux := http.NewServeMux()
	handler.NewOrders(svc).Routes(mux)
	log.Fatal(http.ListenAndServe(":8080", mux))
}
EOF
commit 'test(handler): cover order creation'

python3 - <<'EOF'
p = "internal/handler/orders.go"
s = open(p).read()
a = "\tvar req createRequest\n"
b = "\t\tCurrency:    req.Currency,\n"
assert s.count(a) == 1 and s.count(b) == 1
s = s.replace(
    a,
    "\t// Clients retry on timeouts; the key makes the retry safe.\n"
    "\tkey := r.Header.Get(\"Idempotency-Key\")\n" + a,
)
s = s.replace(b, b + "\t\tIdempotencyKey: key,\n")
open(p, "w").write(s)
EOF
gofmt -w internal/handler/orders.go

# ------------------------------------------------------------ billing-worker
scaffold billing-worker
commit 'chore: init module'

put internal/worker/invoice.go <<'EOF'
package worker

type Invoice struct {
	ID          string `json:"id"`
	CustomerID  string `json:"customer_id"`
	AmountCents int64  `json:"amount_cents"`
	WebhookURL  string `json:"webhook_url"`
}
EOF
commit 'feat(worker): add invoice model'

put internal/worker/retry.go <<'EOF'
package worker

import (
	"context"
	"errors"
	"fmt"
	"time"
)

// ErrPermanent marks failures that another attempt cannot fix.
var ErrPermanent = errors.New("permanent failure")

type Backoff struct {
	Base     time.Duration
	Max      time.Duration
	Attempts int
}

func (b Backoff) delay(attempt int) time.Duration {
	d := b.Base << attempt
	// The shift overflows to a non-positive value on large attempts.
	if d <= 0 || d > b.Max {
		return b.Max
	}
	return d
}

func Retry(
	ctx context.Context,
	b Backoff,
	op func(context.Context) error,
) error {
	if b.Attempts < 1 {
		return errors.New("retry: no attempts configured")
	}
	var err error
	n := 0
	for n < b.Attempts {
		n++
		if err = op(ctx); err == nil {
			return nil
		}
		if errors.Is(err, ErrPermanent) || n == b.Attempts {
			break
		}
		t := time.NewTimer(b.delay(n - 1))
		select {
		case <-ctx.Done():
			t.Stop()
			return fmt.Errorf("retry: %w", ctx.Err())
		case <-t.C:
		}
	}
	return fmt.Errorf("retry: %d attempts: %w", n, err)
}
EOF
put internal/worker/retry_test.go <<'EOF'
package worker

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestRetry(t *testing.T) {
	errTemp := errors.New("temporary")
	tests := []struct {
		name      string
		failures  int
		permanent bool
		cancel    bool
		wantCalls int
		wantErr   error
	}{
		{name: "succeeds on third attempt", failures: 2, wantCalls: 3},
		{
			name:      "permanent error stops at first",
			failures:  5,
			permanent: true,
			wantCalls: 1,
			wantErr:   ErrPermanent,
		},
		{
			name:      "exhausts attempts",
			failures:  9,
			wantCalls: 4,
			wantErr:   errTemp,
		},
		{
			name:      "context cancel",
			failures:  9,
			cancel:    true,
			wantCalls: 1,
			wantErr:   context.Canceled,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			calls := 0
			op := func(context.Context) error {
				calls++
				if tt.cancel {
					cancel()
				}
				if calls <= tt.failures {
					if tt.permanent {
						return ErrPermanent
					}
					return errTemp
				}
				return nil
			}
			b := Backoff{Base: time.Millisecond, Max: 4 * time.Millisecond, Attempts: 4}
			err := Retry(ctx, b, op)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("err = %v, want %v", err, tt.wantErr)
			}
			if calls != tt.wantCalls {
				t.Fatalf("calls = %d, want %d", calls, tt.wantCalls)
			}
		})
	}
}
EOF
commit 'feat(worker): retry with exponential backoff'

put internal/worker/webhook.go <<'EOF'
package worker

import (
	"context"
	"encoding/json"
	"fmt"
)

type Sender interface {
	Send(ctx context.Context, url string, payload []byte) error
}

type Worker struct {
	sender  Sender
	backoff Backoff
}

func NewWorker(s Sender, b Backoff) *Worker {
	return &Worker{sender: s, backoff: b}
}

func (w *Worker) Deliver(ctx context.Context, inv Invoice) error {
	payload, err := json.Marshal(inv)
	if err != nil {
		return fmt.Errorf("deliver invoice %s: marshal: %w", inv.ID, err)
	}
	err = Retry(ctx, w.backoff, func(ctx context.Context) error {
		return w.sender.Send(ctx, inv.WebhookURL, payload)
	})
	if err != nil {
		return fmt.Errorf("deliver invoice %s: %w", inv.ID, err)
	}
	return nil
}
EOF
put cmd/billing-worker/main.go <<'EOF'
package main

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"net/http"
	"time"

	"example.com/billing-worker/internal/worker"
)

type httpSender struct {
	client *http.Client
}

func (s httpSender) Send(ctx context.Context, url string, body []byte) error {
	req, err := http.NewRequestWithContext(
		ctx, http.MethodPost, url, bytes.NewReader(body),
	)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("send webhook: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 && resp.StatusCode < 500 {
		return fmt.Errorf("webhook rejected: %d: %w",
			resp.StatusCode, worker.ErrPermanent)
	}
	if resp.StatusCode >= 500 {
		return fmt.Errorf("webhook failed: %d", resp.StatusCode)
	}
	return nil
}

func main() {
	sender := httpSender{client: &http.Client{Timeout: 5 * time.Second}}
	w := worker.NewWorker(sender, worker.Backoff{
		Base:     500 * time.Millisecond,
		Max:      time.Minute,
		Attempts: 6,
	})
	inv := worker.Invoice{
		ID:          "inv_1001",
		CustomerID:  "cus_42",
		AmountCents: 4900,
		WebhookURL:  "http://localhost:9000/hooks/invoice",
	}
	if err := w.Deliver(context.Background(), inv); err != nil {
		log.Fatal(err)
	}
}
EOF
commit 'feat(worker): deliver invoice webhooks'

# --------------------------------------------------------------- api-gateway
scaffold api-gateway
commit 'chore: init module'

put internal/proxy/proxy.go <<'EOF'
package proxy

import (
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
)

type Route struct {
	Prefix   string
	Upstream *url.URL
}

type entry struct {
	prefix  string
	handler http.Handler
}

type Proxy struct {
	entries []entry
}

func New(routes []Route) *Proxy {
	p := &Proxy{}
	for _, r := range routes {
		p.entries = append(p.entries, entry{
			prefix:  r.Prefix,
			handler: httputil.NewSingleHostReverseProxy(r.Upstream),
		})
	}
	return p
}

func (p *Proxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	for _, e := range p.entries {
		if strings.HasPrefix(r.URL.Path, e.prefix) {
			e.handler.ServeHTTP(w, r)
			return
		}
	}
	http.NotFound(w, r)
}
EOF
put cmd/api-gateway/main.go <<'EOF'
package main

import (
	"log"
	"net/http"
	"net/url"

	"example.com/api-gateway/internal/proxy"
)

func mustParse(raw string) *url.URL {
	u, err := url.Parse(raw)
	if err != nil {
		log.Fatal(err)
	}
	return u
}

func main() {
	p := proxy.New([]proxy.Route{
		{Prefix: "/orders", Upstream: mustParse("http://localhost:8081")},
		{Prefix: "/billing", Upstream: mustParse("http://localhost:8082")},
	})
	log.Fatal(http.ListenAndServe(":8080", p))
}
EOF
commit 'feat(proxy): route by path prefix'

put internal/proxy/proxy_test.go <<'EOF'
package proxy

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
)

func upstream(t *testing.T, name string) *url.URL {
	t.Helper()
	h := func(w http.ResponseWriter, _ *http.Request) {
		_, _ = io.WriteString(w, name)
	}
	srv := httptest.NewServer(http.HandlerFunc(h))
	t.Cleanup(srv.Close)
	u, err := url.Parse(srv.URL)
	if err != nil {
		t.Fatalf("parse upstream url: %v", err)
	}
	return u
}

func TestProxyServeHTTP(t *testing.T) {
	const notFound = "404 page not found\n"
	p := New([]Route{
		{Prefix: "/orders", Upstream: upstream(t, "orders")},
		{Prefix: "/billing", Upstream: upstream(t, "billing")},
	})
	tests := []struct {
		name       string
		path       string
		wantStatus int
		wantBody   string
	}{
		{"orders prefix", "/orders/42", http.StatusOK, "orders"},
		{"billing prefix", "/billing/invoices", http.StatusOK, "billing"},
		{"unknown prefix", "/team/1", http.StatusNotFound, notFound},
		{"root", "/", http.StatusNotFound, notFound},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := httptest.NewRecorder()
			p.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, tt.path, nil))
			if rec.Code != tt.wantStatus {
				t.Fatalf("status = %d, want %d", rec.Code, tt.wantStatus)
			}
			if got := rec.Body.String(); got != tt.wantBody {
				t.Fatalf("body = %q, want %q", got, tt.wantBody)
			}
		})
	}
}
EOF
commit 'test(proxy): cover unknown routes'

put internal/ratelimit/limiter.go <<'EOF'
package ratelimit

import (
	"sync"
	"time"
)

const DefaultBurst = 10

// Limiter is a token bucket refilled at rate tokens per second.
type Limiter struct {
	mu     sync.Mutex
	rate   float64
	burst  float64
	tokens float64
	last   time.Time
	now    func() time.Time
}

func New(rate float64, burst int, now func() time.Time) *Limiter {
	return &Limiter{rate: rate, burst: float64(burst), now: now}
}

func (l *Limiter) Allow() bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := l.now()
	l.tokens = min(l.burst, l.tokens+now.Sub(l.last).Seconds()*l.rate)
	l.last = now
	if l.tokens < 1 {
		return false
	}
	l.tokens--
	return true
}
EOF
put internal/ratelimit/limiter_test.go <<'EOF'
package ratelimit

import (
	"testing"
	"time"
)

func TestLimiterAllow(t *testing.T) {
	tests := []struct {
		name  string
		burst int
		steps []time.Duration
		want  []bool
	}{
		{
			name:  "burst then deny",
			burst: 2,
			steps: []time.Duration{0, 0, 0},
			want:  []bool{true, true, false},
		},
		{
			name:  "refills over time",
			burst: 1,
			steps: []time.Duration{0, 0, time.Second},
			want:  []bool{true, false, true},
		},
		{
			name:  "refill is capped at burst",
			burst: 2,
			steps: []time.Duration{0, 0, 0, time.Hour, 0, 0},
			want:  []bool{true, true, false, true, true, false},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			clock := time.Unix(1792400000, 0)
			l := New(1, tt.burst, func() time.Time { return clock })
			for i, step := range tt.steps {
				clock = clock.Add(step)
				if got := l.Allow(); got != tt.want[i] {
					t.Fatalf("step %d: Allow() = %v, want %v", i, got, tt.want[i])
				}
			}
		})
	}
}
EOF
commit 'feat(ratelimit): add token bucket'

put internal/ratelimit/limiter.go <<'EOF'
package ratelimit

import (
	"sync"
	"time"
)

const DefaultBurst = 10

// Limiter is a token bucket refilled at rate tokens per second.
type Limiter struct {
	mu     sync.Mutex
	rate   float64
	burst  float64
	tokens float64
	last   time.Time
	now    func() time.Time
}

func New(rate float64, burst int, now func() time.Time) *Limiter {
	return &Limiter{rate: rate, burst: float64(burst), tokens: float64(burst), now: now}
}

func (l *Limiter) Allow() bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := l.now()
	// The zero last time would credit centuries of refill on the first call.
	if !l.last.IsZero() {
		l.tokens = min(l.burst, l.tokens+now.Sub(l.last).Seconds()*l.rate)
	}
	l.last = now
	if l.tokens < 1 {
		return false
	}
	l.tokens--
	return true
}
EOF
commit 'fix(ratelimit): refill on first request'

sed -i '' 's/DefaultBurst = 10/DefaultBurst = 20/' internal/ratelimit/limiter.go

# ------------------------------------------------------------------- history
base=1792400000
cmds=(
	'cd ~/code/orders-api'
	'go test ./...'
	'git status'
	'git log --oneline -5'
	'make lint'
	'docker compose up -d'
	'docker compose logs -f api'
	'go build ./...'
	'git diff --stat'
	'curl -s localhost:8080/orders/ord_1'
	'go vet ./...'
	'git pull --rebase'
)
: > $S/run/zsh_history
i=0
for c in $cmds; do
	print -r -- ": $((base + i * 97)):0;$c" >> $S/run/zsh_history
	i=$((i + 1))
done

echo "fixtures: ok"
