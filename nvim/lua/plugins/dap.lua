return {
    "mfussenegger/nvim-dap",
    dependencies = {
        "rcarriga/nvim-dap-ui",
        "nvim-neotest/nvim-nio",
        "leoluz/nvim-dap-go",
        "mfussenegger/nvim-dap-python",
    },
    config = function()
        local dap = require("dap")
        local dapui = require("dapui")

        dapui.setup()

        dap.listeners.after.event_initialized["dapui_config"] = function() dapui.open() end
        dap.listeners.before.event_terminated["dapui_config"] = function() dapui.close() end
        dap.listeners.before.event_exited["dapui_config"] = function() dapui.close() end

        require("dap-go").setup()
        local venv = vim.fn.getcwd() .. "/.venv/bin/python"
        local python = vim.fn.filereadable(venv) == 1 and venv or "python3"
        require("dap-python").setup(python)

        vim.keymap.set("n", "<leader>db", dap.toggle_breakpoint, { desc = "Toggle breakpoint" })
        vim.keymap.set("n", "<leader>dc", dap.continue, { desc = "Continue" })
        vim.keymap.set("n", "<leader>di", dap.step_into, { desc = "Step into" })
        vim.keymap.set("n", "<leader>do", dap.step_over, { desc = "Step over" })
        vim.keymap.set("n", "<leader>dO", dap.step_out, { desc = "Step out" })
        vim.keymap.set("n", "<leader>dr", dap.restart, { desc = "Restart" })
        vim.keymap.set("n", "<leader>dt", dap.terminate, { desc = "Terminate" })
        vim.keymap.set("n", "<leader>du", dapui.toggle, { desc = "Toggle DAP UI" })
    end,
}
