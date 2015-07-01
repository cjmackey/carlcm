# CarlCM (not a serious name)

## Configuration Management for people who like programming

A VERY early work-in-progress experiment with homemade configuration
management; basically, I'd like to take the functionality of something
like Puppet or Chef (solo), and make it more like a library than a
framework.  Right now things only work on Ubuntu and are probably
super buggy and there are a lot of useful methods missing.  Because
this is simply Python code, more complicated things are possible, and
easy things are still easy (to misparaphrase Larry Wall).

Installing:

```
pip install carlcm
```

Running simple idempotent operations is like this:

```python
import carlcm
c = carlcm.ConfigurationManager()
c.file('/home/exampleuser/example.txt', data='Hello World!')
```

Method calls in generally return `True` if they changed something, and
`False` if not.  I might change this in the future.

[On PyPI](https://pypi.python.org/pypi/carlcm)
