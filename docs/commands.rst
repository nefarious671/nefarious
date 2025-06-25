Commands
========

The following commands are available to the agent:

.. list-table::
   :header-rows: 1

   * - Command
     - Description
   * - WRITE_FILE
     - Save content to the outputs directory. Use ``dry_run=true`` to preview.
   * - APPEND_FILE
     - Append text to an existing file.
   * - READ_FILE
     - Read a file from outputs.
   * - READ_LINES
     - Read specific line range from a file.
   * - LIST_OUTPUTS
     - List files under outputs/.
   * - DELETE_FILE
     - Delete a file from outputs/.
   * - EXEC
     - Execute a sandboxed shell command. Use ``dry_run=true`` to preview.
   * - RUN_PYTHON
     - Run Python code inside the sandbox.
   * - WORD_COUNT
     - Count lines and words in a file.
   * - LS
     - Alias for ``LIST_OUTPUTS``.
   * - CAT
     - Alias for ``READ_FILE``.
   * - RM
     - Alias for ``DELETE_FILE``.
   * - WC
     - Alias for ``WORD_COUNT``.
   * - RL
     - Alias for ``READ_LINES``.
   * - HELP
     - Show OS info and command list.
   * - CANCEL
     - Stop recursion with a reason.
   * - PAUSE
     - Pause recursion with a reason.
   * - *(plugins)*
     - Additional commands registered via entry points.

``READ_LINES`` requires numeric ``start`` and ``end`` parameters. If the values
are non-numeric or the range is invalid the command returns an error message.

Both ``WRITE_FILE`` and ``EXEC`` accept a boolean ``dry_run`` parameter to
preview the operation without making changes.
