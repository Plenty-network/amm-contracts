import smartpy as sp

class ContractLibrary(sp.Contract):
    """Provides utility functions 
    """

    def TransferFATwoTokens(sender,receiver,amount,tokenAddress,id):
        """Transfers FA2 tokens
        
        Args:
            sender: sender address
            receiver: receiver address
            amount: amount of tokens to be transferred
            tokenAddress: address of the FA2 contract
            id: id of token to be transferred
        """

        arg = [
            sp.record(
                from_ = sender,
                txs = [
                    sp.record(
                        to_         = receiver,
                        token_id    = id , 
                        amount      = amount 
                    )
                ]
            )
        ]

        transferHandle = sp.contract(
            sp.TList(sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(amount=sp.TNat, to_=sp.TAddress, token_id=sp.TNat).layout(("to_", ("token_id", "amount")))))), 
            tokenAddress,
            entry_point='transfer').open_some()

        sp.transfer(arg, sp.mutez(0), transferHandle)


    def TransferFATokens(sender,reciever,amount,tokenAddress): 
        """Transfers FA1.2 tokens
        
        Args:
            sender: sender address
            reciever: reciever address
            amount: amount of tokens to be transferred
            tokenAddress: address of the FA1.2 contract
        """

        TransferParam = sp.record(
            from_ = sender, 
            to_ = reciever, 
            value = amount
        )

        transferHandle = sp.contract(
            sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
            tokenAddress,
            "transfer"
            ).open_some()

        sp.transfer(TransferParam, sp.mutez(0), transferHandle)

    def TransferToken(sender, receiver, amount, tokenAddress,id, faTwoFlag): 
        """Generic function to transfer any type of tokens
        
        Args:
            sender: sender address
            receiver: receiver address
            amount: amount of tokens to be transferred
            tokenAddress: address of the token contract
            id: id of token to be transferred (for FA2 tokens)
            faTwoFlag: boolean describing whether the token contract is FA2 or not
        """

        sp.verify(amount > 0, "Zero_Transfer")

        sp.if faTwoFlag: 

            ContractLibrary.TransferFATwoTokens(sender, receiver, amount , tokenAddress, id )

        sp.else: 

            ContractLibrary.TransferFATokens(sender, receiver, amount, tokenAddress)


class FA12(ContractLibrary):

    def __init__(self):

        self.init_type(
            sp.TRecord(
                ledger = sp.TBigMap(sp.TAddress,sp.TRecord(approvals = sp.TMap(sp.TAddress, sp.TNat), balance = sp.TNat)),
                metadata = sp.TBigMap(sp.TString,sp.TBytes),
                token_metadata = sp.TBigMap(sp.TNat,sp.TRecord(token_id = sp.TNat, token_info = sp.TMap(sp.TString, sp.TBytes))),
                totalSupply = sp.TNat,
                securityCheck = sp.TBool,
                administrator = sp.TAddress,
                exchangeAddress = sp.TAddress
            )
        )

    @sp.entry_point
    def transfer(self, params):
        sp.set_type(params, sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))))
        sp.verify(
            ( ((params.from_ == sp.sender) |
                 (self.data.ledger[params.from_].approvals[sp.sender] >= params.value))),"FA1.2_Not_Allowed")

        self.addAddressIfNecessary(params.from_)
        self.addAddressIfNecessary(params.to_)

        sp.verify(params.value > 0, "FA1.2_Zero_Transfer")
        sp.verify(params.from_ != params.to_,"FA1.2_Same_Address_Transfer")

        sp.verify(self.data.ledger[params.from_].balance >= params.value,"FA1.2_Insufficient_Balance")
        self.data.ledger[params.from_].balance = sp.as_nat(self.data.ledger[params.from_].balance - params.value)
        self.data.ledger[params.to_].balance += params.value
        sp.if (params.from_ != sp.sender):
            self.data.ledger[params.from_].approvals[sp.sender] = sp.as_nat(self.data.ledger[params.from_].approvals[sp.sender] - params.value)

    @sp.entry_point
    def approve(self, params):
        sp.set_type(params, sp.TRecord(spender = sp.TAddress, value = sp.TNat).layout(("spender", "value")))
        self.addAddressIfNecessary(sp.sender)

        alreadyApproved = self.data.ledger[sp.sender].approvals.get(params.spender, 0)
        sp.verify((alreadyApproved == 0) | (params.value == 0),"FA1.2_Unsafe_Allowance_Change")
        self.data.ledger[sp.sender].approvals[params.spender] = params.value

    def addAddressIfNecessary(self, address):
        sp.if ~self.data.ledger.contains(address):
            self.data.ledger[address] = sp.record(balance = 0, approvals = {})
    
    @sp.utils.view(sp.TNat)
    def getBalance(self, params):
        sp.if self.data.ledger.contains(params):
            sp.result(self.data.ledger[params].balance)
        sp.else:
            sp.result(sp.nat(0))

    @sp.utils.view(sp.TNat)
    def getAllowance(self, params):
        sp.if self.data.ledger.contains(params.owner):
            sp.result(self.data.ledger[params.owner].approvals.get(params.spender, 0))
        sp.else:
            sp.result(sp.nat(0))

    @sp.utils.view(sp.TNat)
    def getTotalSupply(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.totalSupply)

    @sp.entry_point
    def mint(self,params):

        sp.verify(sp.sender == self.data.exchangeAddress,"FA1.2_Not_Exchange")

        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))

        self.addAddressIfNecessary(params.address)

        self.data.ledger[params.address].balance = self.data.ledger[params.address].balance + params.value
        self.data.totalSupply = self.data.totalSupply + params.value

    @sp.entry_point
    def burn(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))

        sp.verify(sp.sender == self.data.exchangeAddress,"FA1.2_Not_Exchange")

        sp.verify(self.data.ledger[params.address].balance >= params.value,"FA1.2_Insufficient_Balance")
        
        self.data.ledger[params.address].balance = sp.as_nat(self.data.ledger[params.address].balance - params.value)
        self.data.totalSupply = sp.as_nat(self.data.totalSupply - params.value)

    @sp.entry_point
    def updateExchangeAddress(self,address): 

        sp.set_type(address, sp.TAddress)
        
        sp.verify(self.is_administrator(sp.sender),"FA1.2_Not_Admin")

        sp.verify(self.data.securityCheck == False,"FA1.2_Cannot_Update")
        
        self.data.exchangeAddress = address

        self.data.securityCheck = True 

    def is_administrator(self, sender):
        return sender == self.data.administrator

    @sp.entry_point
    def RecoverExcessToken(self,params): 

        sp.set_type(params, sp.TRecord( tokenAddress = sp.TAddress, reciever = sp.TAddress, tokenId = sp.TNat, amount = sp.TNat, faTwoCheck = sp.TBool ))

        sp.verify(self.is_administrator(sp.sender),"FA1.2_Not_Admin")

        ContractLibrary.TransferToken(sp.self_address, params.reciever, params.amount, params.tokenAddress, params.tokenId, params.faTwoCheck)

    @sp.entry_point
    def setAdministrator(self, params):
        sp.set_type(params, sp.TAddress)
        sp.verify(self.is_administrator(sp.sender),"FA1.2_Not_Admin")
        self.data.administrator = params

    @sp.utils.view(sp.TAddress)
    def getAdministrator(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.administrator)