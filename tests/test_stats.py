import unittest

from src.monitor.stats import Stats


class TestStats(unittest.TestCase):
    def test_add_packet_and_snapshot(self):
        s = Stats()
        s.add_packet('172.31.66.10', '1.1.1.1', 'TCP', 60, dst_port=80, is_tcp_syn=True)
        snap = s.snapshot()
        self.assertIn('global_proto', snap)
        self.assertGreater(snap['global_proto'].get('TCP', 0), 0)
        self.assertIn('clients', snap)
        self.assertIn('172.31.66.10', snap['clients'])
        c = snap['clients']['172.31.66.10']
        self.assertEqual(c['total_packets'], 1)
        self.assertEqual(c['proto_counts'].get('TCP', 0), 1)
        self.assertIn('endpoints', c)
        self.assertIn('1.1.1.1', c['endpoints'])
        e = c['endpoints']['1.1.1.1']
        self.assertEqual(e['tcp_connections'], 1)
        self.assertTrue(any(p == 80 for p, _cnt in e['top_ports']))


if __name__ == '__main__':
    unittest.main()
