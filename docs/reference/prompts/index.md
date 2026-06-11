# Prompts

::: openfactcheck.prompts
    options:
      members: false
      show_root_heading: false

## Pages

- [`PromptTemplate` class](template.md): the fillable template of chat messages whose content carries `{{variables}}`.
- [`Prompt` class](prompt.md): the filled value, ready to hand to the chat client.
- [Variables](variables.md): the role and variable-contract declarations a template is built from.
- [Codecs](codecs/index.md): the file formats a template loads from and serializes to.
- [Errors](errors.md): exception hierarchy raised while building, loading, or filling a template.
