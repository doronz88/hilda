# Hilda Shortcuts

There are some "shortcuts" you may want to familiarize yourself when using the Hilda's IPython shell.

## Key Bindings

The following key bindings are available:

- **F1**: Show banner help message
- **F2**: Show process state UI
- **F3**: Toggle stdout/stderr enablement
- **F7**: Step Into
- **F8**: Step Over
- **F9**: Continue
- **F10**: Stop

## Magic Functions

Sometimes accessing using the `p` variable can be tiring, so we added some magic functions to help you out!

- `%objc <className>` -
  Equivalent to `className = p.objc_get_class(className)`
- `%fbp <filename> <addressInHex>` -
  Equivalent to `p.file_symbol(addressInHex, filename).bp()`
