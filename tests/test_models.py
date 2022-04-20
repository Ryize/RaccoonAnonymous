import unittest

from models import User


class TestUser(unittest.TestCase):
    def test_login_not_enough_data(self):
        self.assertRaises(ValueError, User.login, 'a', 'a')
        self.assertRaises(ValueError, User.login, 'aaa', 'a')
        self.assertRaises(ValueError, User.login, 'a', 'aaa')
        self.assertRaises(ValueError, User.login, 'aaa', 'aaa')
        self.assertRaises(ValueError, User.login, 'aaaa', 'a')
        self.assertRaises(ValueError, User.login, 'a', 'aaaa')

    def test_login_excess_data(self):
        login = 'a' * 33
        password = 'a' * 97
        self.assertRaises(ValueError, User.login, login, password)
        self.assertRaises(ValueError, User.login, 'login', password)
        self.assertRaises(ValueError, User.login, login, 'password')

    def test_login_wrong_type(self):
        self.assertRaises(ValueError, User.login, 1, 2)
        self.assertRaises(ValueError, User.login, 'aaaa', 1)
        self.assertRaises(ValueError, User.login, 1, 'aaaa')
        self.assertRaises(ValueError, User.login, ['1aaa'], 'aaaa')
        self.assertRaises(ValueError, User.login, 'aaaa', ['1aaa'])
        self.assertRaises(ValueError, User.login, {'dddjdj'}, 'aaaa')
        self.assertRaises(ValueError, User.login, 'aaaa', {'dddjdj'})

if __name__ == '__main__':
    unittest.main()