# -*- mode: python; python-indent: 4 -*-
import ncs


class Main(ncs.application.Application):
    def setup(self):
        self.log.info('Upgrade Main RUNNING')
        with ncs.maapi.Maapi() as m:
            with ncs.maapi.Session(m, 'admin', 'python'):
                with m.start_write_trans() as t:
                    root = ncs.maagic.get_root(t)
                    for service in root.services.l3mplsvpn:
                        # perform upgrade on the existing service instances
                        service.description = "VPN for " + service.customer
                    t.apply()

    def teardown(self):
        self.log.info('Upgrade Main TEARDOWN')

