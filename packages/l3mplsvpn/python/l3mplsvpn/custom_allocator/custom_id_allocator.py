import ncs.template
import ncs.maagic


def id_request(service_path, root):
    """Create an ID allocation request.

    Arguments:
    service_path -- XPath to service instance (not keypath!)
    root -- maagic node referencing the CDB root
    """
    root.l3mplsvpn_requests.create(service_path)


def id_read(tctx, service_path):
    """Read result of an ID allocation request.

    Arguments:
    tctx -- transaction context
    service_path -- path to service instance which requested id
    """
    with ncs.maapi.single_read_trans(tctx.username, tctx.context, db=ncs.OPERATIONAL) as oper_th:
        try:
            oper_root = ncs.maagic.get_root(oper_th)
            allocated_id = oper_root.l3mplsvpn_requests[service_path].allocated_id
        except:
            return None
        return allocated_id





