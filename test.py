from scripts import utilities
class A(object):
    def __init__(self, n):
        self._a = 1
        self._b = 2
        self._n = n

class B(A):
    def __init__(self, n):
        super(B, self).__init__(n)
        
    def main(self):
        print self._a
        print self._n


if __name__ == '__main__':
    f = float(2) / 3
    print f
    ff =  utilities.roundup_2(f)
    print "%.2f" % ff
    b1 = B(100)
    b2 = B(101)
    b3 = B(102)
    s = set([b1, b2, b3])
    s.add(b3)
    c2 = b2
    s.add(c2)
    print s