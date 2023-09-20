# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service
import netaddr


class ServiceCallbacks(Service):

    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

        svi = {'vlan-id': "", 'svi-device': "", 'ip-prefix': "", 'ip-addr': "", 'netmask': ""}

        # proplist object list(tuple(str,str)) to pass information between invocations. We set
        # value for vlan_id in cb_pre_modification and use it here in cb_create.
        svi['vlan-id'] = [x[1] for x in proplist if x[0] == 'vlan-id'][0]

        for device in service.device:
            self.log.info('Service create(SVI device: ', device.name)

            if device.ip_prefix:
                self.log.info('SVI device = ', device.name)

                ip_net = netaddr.IPNetwork(device.ip_prefix)
                ip_addresses = ip_net.iter_hosts()
                
                try:
                    ip_address = str(ip_addresses.next())
                except StopIteration:
                    raise Exception('Not enough IP addresses in specified subnet.')

                self.log.info('Service create(SVI device: ', device.name, ')')

                svi['svi-device'] = device.name
                svi['ip-prefix'] = "{}/{}".format(ip_address, str(ip_net.prefixlen))
                svi['ip-addr'] = ip_address
                svi['netmask'] = str(ip_net.netmask)

                svi_tvars = ncs.template.Variables()
                svi_tvars.add('VLAN-ID', svi['vlan-id'])
                svi_tvars.add('SVI-DEVICE', svi['svi-device'])
                svi_tvars.add('IP-PREFIX', svi['ip-prefix'])
                svi_tvars.add('IP-ADDR', svi['ip-addr'])
                svi_tvars.add('NETMASK', svi['netmask'])
                svi_template = ncs.template.Template(service)
                svi_template.apply('svi-intf-template', svi_tvars)

        vlan_tvars = ncs.template.Variables()
        vlan_tvars.add('VLAN-ID', svi['vlan-id'])
        vlan_template = ncs.template.Template(service)
        vlan_template.apply('svi-vlan-template', vlan_tvars)

        return proplist

    @Service.pre_modification
    def cb_pre_modification(self, tctx, op, kp, root, proplist):
        self.log.info('Service premod(service=', kp, ')')

        if op == ncs.dp.NCS_SERVICE_CREATE:
            self.log.info('Service premod(operation=NCS_SERVICE_CREATE, allocate)')
            vlan_id = root.services.vlan_id_cnt
            proplist.append(('vlan-id', str(vlan_id)))
            self.log.info('Service premod(allocated vlan-id: ', vlan_id, ')')
            root.services.vlan_id_cnt = vlan_id + 1

        elif op == ncs.dp.NCS_SERVICE_DELETE:
            self.log.info('Service premod(operation=NCS_SERVICE_DELETE, skip)')

        return proplist


class Svi(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. Is is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('Svi RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('svi-servicepoint', ServiceCallbacks)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).
        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Svi FINISHED')
