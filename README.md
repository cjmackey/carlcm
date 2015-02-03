# CarlCM (not a serious name)

## Configuration Management for people who like programming

A VERY early work-in-progress experiment with homemade configuration
management; basically, I'd like to take the functionality of something
like Puppet or Chef (solo), and make it more like a library than a
framework.  Right now things only work on Ubuntu and are probably
super buggy and there are a lot of useful methods missing.  Because
this is simply Python code, more complicated things are possible, and
easy things are still easy (to misparaphrase Larry Wall).

Running simple idempotent operations is like this:

```python
import carlcm
c = carlcm.Context()
c.user('exampleuser', random_password=True)
c.file('/home/exampleuser/example.txt', src_data='Hello World!')
```

Method calls in a context generally return `True` if they changed
something, and `False` if not.

I don't know how this would best have new context methods added by
libraries, but for adding others' work to a machine is doable through
a "module" system.  Modules describe some service or intuitive set of
functionality, similar to an Ansible role or Chef cookbook or Puppet
class.  The behavior of modules is super-undecided, but currently
interleaves apt packages from different modules, then each module's
`main` method is run.  I might add something for Consul service
definitions.

The current way of invoking modules... which is pretty ugly but it
works:

```python
import carlcm
c = carlcm.Context()
c.add_modules(carlcm.DockerModule(),
              carlcm.ExampleModule(),
              carlcm.ConsulModule(encrypt='pmsKacTdVOb4x8/Vtr9PWw==',
                                  mode='server', webui=True))
c.run_modules()
```
