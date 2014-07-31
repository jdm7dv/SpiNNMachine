import unittest
import spinn_machine.multicast_routing_entry as mre
import spinn_machine.exceptions as exc


class TestMulticastRoutingEntry(unittest.TestCase):
    def test_creating_new_multicast_routing_entry(self):
        link_ids = list()
        proc_ids = list()
        for i in range(6):
            link_ids.append(i)
        for i in range(18):
            proc_ids.append(i)
        key = 1
        mask = 1
        a_multicast = mre.MulticastRoutingEntry(key, mask, proc_ids, link_ids)

        self.assertEqual(a_multicast.key, key)
        self.assertEqual(a_multicast.link_ids, set(link_ids))
        self.assertEqual(a_multicast.mask, mask)
        self.assertEqual(a_multicast.processor_ids, set(proc_ids))

    def test_duplicate_processors_ids(self):
        with self.assertRaises(exc.SpinnMachineAlreadyExistsException):
            link_ids = list()
            proc_ids = list()
            for i in range(6):
                link_ids.append(i)
            for i in range(18):
                proc_ids.append(i)
            proc_ids.append(0)
            key = 1
            mask = 1
            mre.MulticastRoutingEntry(key, mask, proc_ids, link_ids)

    def test_duplicate_link_ids(self):
        with self.assertRaises(exc.SpinnMachineAlreadyExistsException):
            link_ids = list()
            proc_ids = list()
            for i in range(6):
                link_ids.append(i)
            link_ids.append(3)
            for i in range(18):
                proc_ids.append(i)
            key = 1
            mask = 1
            mre.MulticastRoutingEntry(key, mask, proc_ids, link_ids)

    def test_duplicate_link_ids_and_proc_ids(self):
        with self.assertRaises(exc.SpinnMachineAlreadyExistsException):
            link_ids = list()
            proc_ids = list()
            for i in range(6):
                link_ids.append(i)
            link_ids.append(3)
            for i in range(18):
                proc_ids.append(i)
            proc_ids.append(0)
            key = 1
            mask = 1
            mre.MulticastRoutingEntry(key, mask, proc_ids, link_ids)

    def test_merger(self):
        link_ids = list()
        link_ids2 = list()
        proc_ids = list()
        proc_ids2 = list()
        for i in range(3):
            link_ids.append(i)
        for i in range(3, 6):
            link_ids2.append(i)
        for i in range(9):
            proc_ids.append(i)
        for i in range(9, 18):
            proc_ids2.append(i)
        key = 1
        mask = 1
        a_multicast = mre.MulticastRoutingEntry(key, mask, proc_ids, link_ids)
        b_multicast = mre.MulticastRoutingEntry(key, mask, proc_ids2, link_ids2)

        result_multicast = a_multicast.merge(b_multicast)
        comparison_link_ids = list()
        comparison_proc_ids = list()
        for i in range(6):
            comparison_link_ids.append(i)
        self.assertEqual(link_ids + link_ids2, comparison_link_ids)
        for i in range(18):
            comparison_proc_ids.append(i)
        self.assertEqual(proc_ids + proc_ids2, comparison_proc_ids)

        self.assertEqual(result_multicast.key, key)
        self.assertEqual(result_multicast.link_ids, set(comparison_link_ids))
        self.assertEqual(result_multicast.mask, mask)
        self.assertEqual(result_multicast.processor_ids,
                         set(comparison_proc_ids))

    def test_merger_with_invalid_parameter_key(self):
        with self.assertRaises(exc.SpinnMachineInvalidParameterException):
            link_ids = list()
            link_ids2 = list()
            proc_ids = list()
            proc_ids2 = list()
            for i in range(3):
                link_ids.append(i)
            for i in range(3, 6):
                link_ids2.append(i)
            for i in range(9):
                proc_ids.append(i)
            for i in range(9, 18):
                proc_ids2.append(i)
            key = 1
            mask = 1
            a_multicast = mre.MulticastRoutingEntry(key, mask, proc_ids,
                                                    link_ids)
            b_multicast = mre.MulticastRoutingEntry(key + 1, mask, proc_ids2,
                                                    link_ids2)

            a_multicast.merge(b_multicast)

    def test_merger_with_invalid_parameter_mask(self):
        with self.assertRaises(exc.SpinnMachineInvalidParameterException):
            link_ids = list()
            link_ids2 = list()
            proc_ids = list()
            proc_ids2 = list()
            for i in range(3):
                link_ids.append(i)
            for i in range(3, 6):
                link_ids2.append(i)
            for i in range(9):
                proc_ids.append(i)
            for i in range(9, 18):
                proc_ids2.append(i)
            key = 1
            mask = 1
            a_multicast = mre.MulticastRoutingEntry(key, mask, proc_ids,
                                                    link_ids)
            b_multicast = mre.MulticastRoutingEntry(key, mask + 1, proc_ids2,
                                                    link_ids2)

            a_multicast.merge(b_multicast)


if __name__ == '__main__':
    unittest.main()
