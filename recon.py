import copy
import dataclasses


@dataclasses.dataclass
class Position:
    symbol: str
    shares: float = dataclasses.field(default=0.0)

    def __post_init__(self):
        self.shares = format_num(float(self.shares))


@dataclasses.dataclass
class Transaction:
    symbol: str
    action: str
    shares: float
    value: float

    def __post_init__(self):
        self.shares = format_num(float(self.shares))
        self.value = format_num(float(self.value))


class Account:
    def __init__(self, file_name):
        self.D0_POS = {}
        self.D1_TRN = {}
        self.D1_POS = {}
        self.reconciliations = {}
        self.import_records(file_name)
        self.final_positions = copy.deepcopy(self.D0_POS)

    def import_records(self, file_name='recon.in'):
        """ Import position and transaction records from 'recon.in' file
        into the Account instance's D0_POS, D1_TRN and D1_POS dictionaries.

        >>> account.D0_POS == {'AAPL': Position(symbol='AAPL', shares=100), 'GOOG': Position(symbol='GOOG', shares=200), 'SP500': Position(symbol='SP500', shares=175.75), 'Cash': Position(symbol='Cash', shares=1000)}
        True
        >>> account.D1_TRN == {'AAPL': [Transaction(symbol='AAPL', action='SELL', shares=100, value=30000)], 'GOOG': [Transaction(symbol='GOOG', action='BUY', shares=10, value=10000), Transaction(symbol='GOOG', action='DIVIDEND', shares=0, value=50)], 'Cash': [Transaction(symbol='Cash', action='DEPOSIT', shares=0, value=1000), Transaction(symbol='Cash', action='FEE', shares=0, value=50)], 'TD': [Transaction(symbol='TD', action='BUY', shares=100, value=10000)]}
        True
        >>> account.D1_POS == {'GOOG': Position(symbol='GOOG', shares=220), 'SP500': Position(symbol='SP500', shares=175.75), 'Cash': Position(symbol='Cash', shares=20000), 'MSFT': Position(symbol='MSFT', shares=10)}
        True

        """
        with open(file_name, 'r') as f:
            record_key = 'no key'
            for record in f:
                parsed_record = parse_record(record.strip())
                if (parsed_record[1] == 'TRN') or (parsed_record[1] == 'POS'):
                    record_key = parsed_record[0] + '_' + parsed_record[1]
                else:
                    new_record = create_record(*parsed_record)
                    init_record(new_record, self.__getattribute__(record_key))

    def apply_transactions(self):
        """ Apply D1_TRN transactions to D0_POS positions. D0_POS is unaltered,
            positions with transactions applied are stored in final_positions.

        >>> account.apply_transactions()
        >>> account.final_positions == {'AAPL': Position(symbol='AAPL', shares=0), 'GOOG': Position(symbol='GOOG', shares=210), 'SP500': Position(symbol='SP500', shares=175.75), 'Cash': Position(symbol='Cash', shares=12000), 'TD': Position(symbol='TD', shares=100)}
        True

        """
        for transactions in self.D1_TRN.values():
            [self.actions[transaction.action](self, transaction) for transaction in transactions]

    def recon_to_file(self):
        """ Creates a file called 'recon.out'.
        >>> import os.path
        >>> os.path.isfile('recon.out')
        True

        """
        positions = ['{symbol} {shares}\n'.format(symbol=position.symbol, shares=position.shares) for position in self.reconciliations.values()]

        with open('recon.out', 'w') as f:
            out = ''.join(positions)
            f.write(out)
            return out

    def credit(self, transaction):  # deposit, dividend, sell
        """ Add transaction value to Cash position's shares.
        >>> account.final_positions['Cash'].shares = 0
        >>> account.credit(Transaction('Cash', 'DEPOSIT', 0, 42))
        >>> account.final_positions['Cash'].shares == 42
        True
        """
        if 'Cash' not in self.final_positions:
            self.final_positions['Cash'] = Position('Cash')
        else:
            self.final_positions['Cash'].shares += transaction.value

    def debit(self, transaction):  # fee, buy
        """ Subtract transaction value from Cash position's shares.
            >>> account.final_positions['Cash'].shares = 42
            >>> account.debit(Transaction('Cash', 'FEE', 0, 42))
            >>> account.final_positions['Cash'].shares == 0
            True
        """
        if 'Cash' not in self.final_positions:
            self.final_positions['Cash'] = Position('Cash', self.D0_POS['Cash'][0].shares - (-1 * transaction.value))
        else:
            self.final_positions['Cash'].shares -= transaction.value

    def sell(self, transaction):
        """ Subtract transaction shares from respective position's shares.
        >>> account.sell(Transaction('AAPL', 'SELL', 10, 300))
        >>> account.final_positions['AAPL'].shares == 90
        True

        """
        applied_transaction = Position(transaction.symbol)
        if transaction.symbol not in self.D0_POS:
            shares = 0
        else:
            shares = self.D0_POS[transaction.symbol].shares

        applied_transaction.shares = shares - transaction.shares

        self.final_positions[transaction.symbol] = applied_transaction
        self.credit(transaction)

    def buy(self, transaction):
        """ Subtract transaction shares from respective position's shares.
        >>> account.buy(Transaction('AAPL', 'Buy', 10, 300))
        >>> account.final_positions['AAPL'].shares == 110
        True

        """
        applied_transaction = Position(transaction.symbol)
        if transaction.symbol not in self.D0_POS:
            shares = 0
        else:
            shares = self.D0_POS[transaction.symbol].shares

        applied_transaction.shares = shares + transaction.shares

        self.final_positions[transaction.symbol] = applied_transaction
        self.debit(transaction)

    def recon_positions(self):
        """ Reconciles given D1_POS with expected values in reconciliations.
        >>> position1 = Position('PEGI', 10)
        >>> position2 = Position('NTDOY', 15)
        >>> account.D1_POS = {}
        >>> account.final_positions = {}
        >>> init_record(position1, account.D1_POS)
        >>> init_record(position2, account.final_positions)
        >>> account.recon_positions()
        >>> 'PEGI' in account.reconciliations
        True
        >>> account.reconciliations['PEGI'].shares == 10
        True
        >>> 'NTDOY' in account.reconciliations
        True
        >>> account.reconciliations['NTDOY'].shares == -15
        True
        """
        for position in self.D1_POS.values():
            if position.symbol not in self.final_positions:
                self.reconciliations[position.symbol] = copy.deepcopy(position)
            elif self.final_positions[position.symbol].shares != position.shares:
                recon_pos = copy.deepcopy(position)
                recon_pos.shares -= self.final_positions[position.symbol].shares
                self.reconciliations[position.symbol] = recon_pos

        for position in self.final_positions.values():
            if position.symbol not in self.D1_POS and position.shares != 0:
                recon_pos = copy.deepcopy(position)
                recon_pos.shares *= -1
                self.reconciliations[position.symbol] = recon_pos

    actions = dict(
        SELL=sell,
        BUY=buy,
        DEPOSIT=credit,
        FEE=debit,
        DIVIDEND=credit
    )


def create_record(a=None, b=None, c=None, d=None):
    """ Create the correct position or transaction record from an uncertain number of arguments.
    >>> record1 = create_record('AMZN', 50)
    >>> isinstance(record1, Position)
    True
    >>> record2 = create_record('ETSY', 'BUY', 100, 6980)
    >>> isinstance(record2, Transaction)
    True
    """
    if d:
        return Transaction(a, b, c, d)
    else:
        return Position(a, b)


def parse_record(record):
    """ Separate record string into its parts.
    >>> record1 = parse_record('IBM BUY 10 1370.04')
    >>> len(record1) == 4
    True
    >>> record2 = parse_record('AMD 20')
    >>> len(record2) == 2
    True
    >>> record3 = parse_record('D1-POS')
    >>> len(record3) == 2
    True
    >>> record3[0] == 'D1' and record3[1] == 'POS'
    True
    """
    return record.replace('-', ' ').split(' ')


def format_num(num):
    """ Returns either an int or float version of the number, for display purposes,
    as shares and values are floats by default.
    >>> format_num(5)
    5
    >>> format_num(4.1)
    4.1
    """
    if int(num) == num:
        return int(num)
    else:
        return num


def init_record(record, collection):
    """ For transactions, the record is added to a list or that symbol.
    If it's the first transaction record for that symbol,
    then init_record creates the list for that symbol
    and adds the transaction record to it.

    For positions, the record is added to the respective dictionary.
    >>> record1 = Position('KO', 10)
    >>> record2 = Transaction('GE', 'BUY', 100, 909)
    >>> record3 = Transaction('GE', 'BUY', 200, 1818)
    >>> init_record(record1, account.D0_POS)
    >>> init_record(record2, account.D1_TRN)
    >>> init_record(record3, account.D1_TRN)
    >>> account.D1_TRN['GE'][0].value == 909
    True
    >>> account.D1_TRN['GE'][1].value == 1818
    True
    >>> account.D0_POS['KO'].shares == 10
    True
    """
    if isinstance(record, Transaction):
        if record.symbol in collection:
            collection[record.symbol].append(record)
        else:
            collection[record.symbol] = [record]
    else:
        collection[record.symbol] = record


def main():
    account = Account('recon.in')
    account.apply_transactions()
    account.recon_positions()
    account.recon_to_file()


def _test():




if __name__ == "__main__":
    import doctest
    main()
doctest.testmod(extraglobs={'account': Account('recon.in')})