# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service
from resource_manager import id_allocator

TYPE_CISCO_IOS = '{tailf-ned-cisco-ios}'
TYPE_CISCO_IOSXR = '{tailf-ned-cisco-ios-xr}'


# ------------------------
# SERVICE CALLBACK EXAMPLE
# ------------------------
class ServiceCallbacks(Service):

    # The create() callback is invoked inside NCS FASTMAP and must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

        service_path = "/services/l3mplsvpn[name='{}']".format(service.name)
        id_allocator.id_request(service, service_path, tctx.username, 'vpn-id', service.name, False)
        vpn_id = id_allocator.id_read(tctx.username, root, 'vpn-id', service.name)
        if vpn_id is None:
            self.log.info('Service create(vpn-id does not exist, waiting for redeploy)')
            return proplist

        self.log.info('Service create(start building device configuration)')
        for link in service.link:

            vpn_link = {'pe-ip': link.pe_ip, 'ce-ip': link.ce_ip, 'rip-net': link.rip_net}
            device_type = get_device_type(root, link.device)

            # Calculate IP address from unique link ID: 172.x.y.z
            pe_ip_o2 = 16 + link.link_id / 4096         # Second octet
            pe_ip_o3 = (link.link_id % 4096) / 16       # Third octet
            pe_ip_o4 = (link.link_id % 16) * 16 + 1     # Fourth octet
            ce_ip_o4 = pe_ip_o4 + 1                     # Fourth octet for CE side ( = PE + 1 )

            if not link.pe_ip:
                vpn_link['pe-ip'] = '172.{}.{}.{}'.format(pe_ip_o2, pe_ip_o3, pe_ip_o4)
            if not link.ce_ip:
                vpn_link['ce-ip'] = '172.{}.{}.{}'.format(pe_ip_o2, pe_ip_o3, ce_ip_o4)
            if not link.rip_net:
                vpn_link['rip-net'] = '172.{}.0.0'.format(pe_ip_o2)

            tvars = ncs.template.Variables()
            template = ncs.template.Template(service)
            tvars.add('VPNID', vpn_id)
            tvars.add('DEVICE', link.device)
            tvars.add('PEIP', vpn_link['pe-ip'])
            tvars.add('CEIP', vpn_link['ce-ip'])
            tvars.add('ROUTING-PROTOCOL', link.routing_protocol)

            if link.routing_protocol == 'rip':
                tvars.add('RIP-NET', vpn_link['rip-net'])
            else:
                tvars.add('RIP-NET', '')

            if device_type == TYPE_CISCO_IOS:
                tvars.add('INTERFACE', link.ios.interface)
                self.log.info('Service create(applying IOS template for device ', link.device, ')')
                template.apply('l3mplsvpn-ios-template', tvars)
            elif device_type == TYPE_CISCO_IOSXR:
                tvars.add('INTERFACE', link.iosxr.interface)
                self.log.info('Service create(applying IOS-XR template for device ', link.device, ')')
                template.apply('l3mplsvpn-iosxr-template', tvars)
            else:
                raise Exception('Service create(Unknown device type: ' + device_type, ')')

        return proplist


def get_device_type(root, device):
    # Return module used by device, to determine device type
    modules = root.devices.device[device].module.keys()
    return str(modules[0])


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class L3MplsVpn(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. It is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('L3MplsVpn RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('l3mplsvpn-servicepoint', ServiceCallbacks)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).

        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('L3MplsVpn FINISHED')
