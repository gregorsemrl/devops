# -*- mode: python; python-indent: 4 -*-

import ncs
import ncs.maapi
import ncs.experimental
import _ncs
import fake_external_allocator


# ------------------------------------------------
# SUBSCRIBER ITERATOR OBJECT
# ------------------------------------------------
class AllocatorSubscriber(ncs.experimental.Subscriber):
    """This subscriber subscribes to changes in the l3mplsvpn-requests structure
    and takes care of requesting and providing vlan-ids for l3mplsvpn service."""

    # custom initializer which gets called from the
    # constructor (__init__)
    def init(self):
        self.service_path = '/l3mplsvpn-requests'
        self.register(self.service_path, priority=100)

    # Initiate your local state
    def pre_iterate(self):
        self.log.info('AllocatorSubscriber: pre_iterate')
        return []

    # Iterate over the change set
    def iterate(self, keypath, operation, oldval, newval, state):
        self.log.debug('iterate: {} {} old:{} new:{}'.format(operation, keypath, oldval, newval))
        if operation == ncs.MOP_CREATED:
            state.append({'operation': 'create', 'path': str(keypath)})
            return ncs.ITER_CONTINUE
        elif operation == ncs.MOP_DELETED:
            try:
                with ncs.maapi.single_read_trans('admin', 'system', db=ncs.OPERATIONAL) as t:
                    val = t.get_elem(str(keypath) + '/allocated-id')
                    state.append({'operation': 'delete', 'path': str(keypath), 'value': val})
            except Exception as e:
                self.log.error('Error in iterate: ', e)
            return ncs.ITER_CONTINUE

        return ncs.ITER_RECURSE

    # This will run in a separate thread to avoid a transaction deadlock
    def post_iterate(self, state):
        self.log.info('AllocatorSubscriber: post_iterate, state=', state)

        for request in state:
            if request['operation'] == 'create':
                allocated_id = fake_external_allocator.allocate_id()
                self.log.info('Allocated pwid ', allocated_id)
                path = request['path'] + '/allocated-id'

                with ncs.maapi.single_write_trans('admin', 'system', db=ncs.OPERATIONAL) as t:
                    t.set_elem(_ncs.Value(allocated_id, _ncs.C_UINT32), path)
                    t.apply()

                    service_path = t.get_elem(request['path'] + '/service-path')
                    service_path = str(service_path) + '/reactive-re-deploy'
                    self.log.info('Redeploying ', service_path)
                    redeploy = ncs.maagic.get_node(t, service_path)
                    redeploy()
            elif request['operation'] == 'delete':
                fake_external_allocator.deallocate_id(request['value'])
                self.log.info('Deallocated pwid ', request['value'])

    # determine if post_iterate() should run
    def should_post_iterate(self, state):
        return state != []

    def cleanup(self):
        pass


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class L3MplsVpnSubscriber(ncs.application.Application):
    def setup(self):
        self.log.info('cusotom-allocator RUNNING')
        self.sub = AllocatorSubscriber(app=self)
        self.sub.start()

    def teardown(self):
        self.log.info('custom-allocator FINISHED')
