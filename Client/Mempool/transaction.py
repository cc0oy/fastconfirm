import time


class transaction:
    '''
    creater=''  #hash value of sender
    receiver='' #hash value of receiver
    tx_id=''   #pointer of the transaction
    tx_money=0
    txfee=0 #transaction fee
    time='' #time of creating transaction
    '''

    def __init__(self, c, r, tx, m, f, t):
        self.creater = c
        self.receiver = r
        self.tx_id = tx
        self.tx_money = m
        self.txfee = f
        # localtime = time.asctime(time.localtime(time.time()))
        self.time = t
