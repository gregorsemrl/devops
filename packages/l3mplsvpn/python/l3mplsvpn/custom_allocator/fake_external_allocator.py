#!/usr/bin/env python

import ncs.maapi
import ncs.maagic

"""This simulates external inventory of vlan-ids 
while actually all needed data is in CDB."""


def allocate_id():
    with ncs.maapi.single_write_trans('admin', 'system') as t:
        root = ncs.maagic.get_root(t)
        db = root.id_database
        try:
            used_ids = db.used_ids.as_list()
            allocated_id = [n for n in range(db.start, db.stop) if n not in used_ids][0]
            used_ids.append(allocated_id)
            db.used_ids = used_ids
            t.apply()
            return allocated_id
        except IndexError:
            raise Exception('Exhausted all IDs!')


def deallocate_id(i):
    with ncs.maapi.single_write_trans('admin', 'system') as t:
        root = ncs.maagic.get_root(t)
        db = root.id_database
        used_ids = db.used_ids.as_list()
        try:
            used_ids.remove(i)
            db.used_ids = used_ids
            t.apply()
        except ValueError:
            pass
