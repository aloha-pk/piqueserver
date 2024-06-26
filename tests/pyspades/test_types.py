from pyspades.types import IDPool, AttributeSet, OutOfIDsException
import unittest


class TestIDPool(unittest.TestCase):
    def test_start(self):
        pool = IDPool(start=5)
        self.assertEqual(5, pool.pop())

    def test_putting_back(self):
        pool = IDPool(start=5)
        self.assertEqual(5, pool.pop())
        self.assertEqual(6, pool.pop())
        pool.put_back(5)
        self.assertEqual(5, pool.pop())

    def test_out_of_ids(self):
        pool = IDPool(start=0, end=4)
        pool.pop()
        pool.pop()
        pool.pop()
        pool.pop()
        self.assertRaises(OutOfIDsException, pool.pop)
        pool.put_back(0)
        self.assertEqual(0, pool.pop())

class TestAttributeSet(unittest.TestCase):
    def test_set(self):
        atset = AttributeSet(["test", "set", "name"])
        self.assertTrue(atset.test)
        self.assertTrue(atset.set)
        self.assertTrue(atset.name)
        self.assertFalse(atset.wrong)

        self.assertFalse(atset.new)
        atset.new = False
        self.assertFalse(atset.new)
        atset.new = True
        self.assertTrue(atset.new)
        atset.new = 0
        self.assertFalse(atset.new)
