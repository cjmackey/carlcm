
import carlcm

if __name__ == '__main__':
    c = carlcm.Context()

    c.add_modules(carlcm.DockerModule(),
                  carlcm.ExampleModule(),
                  carlcm.ConsulModule(encrypt='pmsKacTdVOb4x8/Vtr9PWw==',
                                      mode='server', webui=True))

    c.run_modules()
