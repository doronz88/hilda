# Hilda Objective-C Support

## Objective-C Classes

The same as symbols applies to Objective-C classes name resolution. You can either:

```python
d = NSDictionary.new()  # Call its `new` selector

# Which is equivalent to:
NSDictionary = p.objc_get_class('NSDictionary')
d = NSDictionary.new()

# Or you can use the IPython magic function
%objc
NSDictionary
```

This is possible only since `NSDictionary` is exported. In case it is not, you must call `objc_get_class()` explicitly.

As you can see, you can directly access all the class' methods.

Please look what more stuff you can do as shown below:

```python
# Show the class' ivars
print(NSDictionary.ivars)

# Show the class' methods
print(NSDictionary.methods)

# Show the class' properties
print(NSDictionary.properties)

# View class' selectors which are prefixed with 'init'
print(NSDictionary.methods.filter_startswith('init'))

# You can of course use any of `SymbolList` over them, for example:
# this will `po` (print object) all those selectors returned value
NSDictionary.methods.filter_startswith('init').monitor(retval='po')

# Monitor each time any selector in NSDictionary is called
NSDictionary.monitor()

# `force_return` for some specific selector with a hard-coded value (4)
NSDictionary.methods.get('valueForKey:').address.monitor(force_return=4)

# Capture the `self` object at the first hit of any selector
# `True` for busy-wait for object to be captured
dictionary = NSDictionary.capture_self(True)

# Print a colored and formatted version for class layout
dictionary.show()
```

## Objective-C Objects

In order to work with Objective-C objects, each symbol contains a property called
`objc_symbol`. After calling, you can work better with each object:

```python
dict = NSDictionary.new().objc_symbol
dict.show()  # Print object layout

# Just like class, you can access its ivars, method, etc...
print(dict.ivars)

# Except now they have values you can view
print(dict._ivarName)

# Or edit
dict._ivarName = value

# And of course you can call the object's methods
# Hilda will checks if the method returned an Objective-C object:
#   - If so, call `objc_symbol` upon it for you
#   - Otherwise, leave it as a simple `Symbol` object
arr = dict.objectForKey_('keyContainingNSArray')

# You can also call class-methods
# Hilda will call it using either the instance object,
# or the class object respectively of the use
newDict = dict.dictionary()

# Print the retrieved object
print(arr.po())
```

Also, working with Objective-C objects like this can be somewhat exhausting, so we created the `ns`/`cf`
helpers for building Foundation objects from Python values, plus `decode_cf()` and `Symbol.py()` for
converting them back:

```python
import datetime

# Using `ns`/`cf` we can just pass a Python dictionary
function_requiring_a_specific_dictionary(p.ns({
    'key1': 'string',  # will convert to NSString
    'key2': True,      # will convert to NSNumber
    'key3': b'1234',   # will convert to NSData
    'key4': datetime.datetime(2021, 1, 1)  # will convert to NSDate
}))

# And also parse one back into Python
normal_python_dict = p.decode_cf(p.ns({
    'key1': 'string',  # will convert to NSString
    'key2': True,      # will convert to NSNumber
    'key3': b'1234',   # will convert to NSData
    'key4': datetime.datetime(2021, 1, 1)  # will convert to NSDate
}))

# Equivalent shortcut when you already have a Symbol
normal_python_dict = p.ns({
    'key1': 'string',
    'key2': True,
    'key3': b'1234',
    'key4': datetime.datetime(2021, 1, 1)
}).py()
```

As a last resort, if the object is not serializable for this to work, you can just run pure Objective-C code:

```python
# Let LLDB compile and execute the expression
abc_string = p.evaluate_expression('[NSString stringWithFormat:@"abc"]')

# Will print "abc"
print(abc_string.po())
```
