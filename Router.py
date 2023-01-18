import smartpy as sp 

CONSTANT = 10**32

class ErrorMessages:

    def make(s): 
        """Generates standard error messages prepending contract name (PlentySwap_)
        Args:
            s: error message string
        Returns:
            standardized error message
        """

        return ("Plenty_Network_Router_" + s)

    
    NotAdmin = make("Not_Admin")

    Insufficient = make("Insufficient_Balance")

    NotInitialized = make("Not_Initialized")

    Paused = make("Paused_State")

    BadState = make("Bad_State")

    SmallRoute = make("Small_Route")

    ZeroBalance = make("Zero_Swap")

    InvalidExchange = make("Invalid_Exchange")

    Slippage = make("Slippage")

class Balance_of:
    def request_type():
        return sp.TRecord(
            owner = sp.TAddress,
            token_id = sp.TNat).layout(("owner", "token_id"))
    def response_type():
        return sp.TList(
            sp.TRecord(
                request = Balance_of.request_type(),
                balance = sp.TNat).layout(("request", "balance")))
    def entry_point_type():
        return sp.TRecord(
            callback = sp.TContract(Balance_of.response_type()),
            requests = sp.TList(Balance_of.request_type())
        ).layout(("requests", "callback"))

class ContractLibrary(sp.Contract, ErrorMessages,Balance_of): 
    
    def TransferFATwoTokens(sender,reciever,amount,tokenAddress,id):

        arg = [
            sp.record(
                from_ = sender,
                txs = [
                    sp.record(
                        to_         = reciever,
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

    def TransferToken(sender, reciever, amount, tokenAddress,id, faTwoFlag):

        sp.if faTwoFlag: 

            ContractLibrary.TransferFATwoTokens(sender, reciever, amount , tokenAddress, id )

        sp.else: 

            ContractLibrary.TransferFATokens(sender, reciever, amount, tokenAddress)

    def approveCall(tokenAddress, approveAmount, spender): 

        approveData = sp.record(
            spender = spender,
            value = approveAmount
        )

        approveHandle = sp.contract(
            sp.TRecord(spender = sp.TAddress, value = sp.TNat).layout(("spender", "value")),
            tokenAddress,
            "approve"
            ).open_some()

        sp.transfer(approveData, sp.mutez(0), approveHandle)

    def updateFaTwo(owner,exchangeAddress,tokenAddress,tokenId,operationType): 
    
        contractHandle = sp.contract(
            sp.TList(
            sp.TVariant(
                add_operator = sp.TRecord(
                    owner = sp.TAddress,
                    operator = sp.TAddress,
                    token_id = sp.TNat).layout(("owner", ("operator", "token_id"))),
                remove_operator = sp.TRecord(
                    owner = sp.TAddress,
                    operator = sp.TAddress,
                    token_id = sp.TNat).layout(("owner", ("operator", "token_id")))
            )
        ),
        tokenAddress,
        "update_operators"
        ).open_some()

        sp.if operationType: 
            
            contractData = [
                sp.variant("add_operator", sp.record(
                owner = owner,
                operator = exchangeAddress,
                token_id = tokenId)),
            ]   

            sp.transfer(contractData, sp.mutez(0), contractHandle)

        sp.else: 

            contractData = [
                sp.variant("remove_operator", sp.record(
                    owner = owner,
                    operator = exchangeAddress,
                    token_id = tokenId)),
            ]

            sp.transfer(contractData, sp.mutez(0), contractHandle)

    def getBalance(tokenAddress, tokenId, tokenType):
        
        sp.if tokenType:
            
            contract = sp.contract(
                Balance_of.entry_point_type(),
                tokenAddress,
                entry_point = "balance_of"
            ).open_some(message = "InvalidTokenInterface")

            args = sp.record(
                callback = sp.contract(
                    Balance_of.response_type(),
                    sp.self_address,
                    entry_point = "faTwoCallBack").open_some(),
                requests    = [
                    sp.record(
                        owner       = sp.self_address,
                        token_id    = tokenId,
                    )
                ]
            )
            sp.transfer(args, sp.mutez(0), contract)

        sp.else:

            param = (sp.self_address, sp.self_entry_point(entry_point = "faOneCallBack"))

            contractHandle = sp.contract(
                sp.TPair(sp.TAddress, sp.TContract(sp.TNat)),
                tokenAddress,
                "getBalance",      
            ).open_some()
        
            sp.transfer(param, sp.mutez(0), contractHandle)

class Router(ContractLibrary):

    def __init__(self,_adminAddress, _ctezTokenAddress, _ctezFlatCurve):

        self.init(
            adminAddress = sp.set([_adminAddress]),
            ctezTokenAddress = _ctezTokenAddress,
            ctezFlatCurve = _ctezFlatCurve,
            paused = False,
            Lock = False,
            recipient = sp.none,
            Registry = sp.big_map(
                tvalue = sp.TRecord(token1Address = sp.TAddress, token2Address = sp.TAddress, token1Id = sp.TNat, token2Id = sp.TNat, token1Type = sp.TBool, token2Type = sp.TBool ),
                tkey = sp.TAddress
            ),
            Route = sp.map(
                tvalue = sp.TRecord(exchangeAddress = sp.TAddress, requiredTokenAddress = sp.TAddress, requiredTokenId = sp.TNat,minimumOutput = sp.TNat),
                tkey = sp.TNat
            ),
            counter = sp.nat(0)
        )
    
    @sp.entry_point
    def routerSwap(self,params):

        sp.set_type(params, sp.TRecord(
            recipient = sp.TAddress,
            SwapAmount = sp.TNat,
            Route = sp.TMap(
                sp.TNat,
                sp.TRecord(exchangeAddress = sp.TAddress, requiredTokenAddress = sp.TAddress, requiredTokenId = sp.TNat,minimumOutput = sp.TNat)
            )
        ))

        sp.verify(~ self.data.paused, ErrorMessages.Paused)

        sp.verify(~ self.data.Lock, ErrorMessages.BadState)

        sp.verify(sp.len(params.Route) > 0, ErrorMessages.SmallRoute)

        # Changing State

        self.data.Lock = True 

        self.data.Route = params.Route

        self.data.recipient = sp.some(params.recipient)

        # Call Swap Function 
        
        self.Swap(self.data.Route[self.data.counter].exchangeAddress, params.SwapAmount, 
        self.data.Route[self.data.counter].requiredTokenAddress,self.data.Route[self.data.counter].requiredTokenId, self.data.Route[self.data.counter].minimumOutput)


    def Swap(self,exchangeAddress, swapAmount, requiredTokenAddress, requiredTokenId, minimumOutput):

        sp.if exchangeAddress == self.data.ctezFlatCurve:

            sp.if requiredTokenAddress == self.data.ctezTokenAddress:

                sp.verify(sp.utils.nat_to_mutez(swapAmount) == sp.amount)

                contractHandle = sp.contract(
                    sp.TRecord(minCashBought = sp.TNat, recipient = sp.TAddress),
                    self.data.ctezFlatCurve,
                    "tez_to_ctez"
                ).open_some()

                sp.if self.data.counter + 1 == sp.len(self.data.Route):

                    contractData = sp.record(minCashBought = minimumOutput, recipient = self.data.recipient.open_some())

                    sp.transfer(contractData, sp.utils.nat_to_mutez(swapAmount), contractHandle)

                    self.data.Lock = False

                    self.data.Route = sp.map()

                    self.data.recipient = sp.none

                    self.data.counter = 0

                sp.else:

                    contractData = sp.record(minCashBought = minimumOutput, recipient = sp.self_address)

                    sp.transfer(contractData, sp.utils.nat_to_mutez(swapAmount), contractHandle)

                    ContractLibrary.getBalance(requiredTokenAddress,requiredTokenId, False)

            sp.else:

                contractData = sp.record(
                    cashSold = swapAmount,
                    minTezBought = minimumOutput,
                    recipient = self.data.recipient.open_some())

                contractHandle = sp.contract(
                    sp.TRecord(cashSold = sp.TNat, minTezBought = sp.TNat, recipient = sp.TAddress),
                    self.data.ctezFlatCurve,
                    "ctez_to_tez"
                ).open_some()

                sp.transfer(contractData, sp.mutez(0), contractHandle)

                sp.verify(self.data.counter + 1 == sp.len(self.data.Route))

                # Reset Lock

                self.data.Lock = False

                self.data.Route = sp.map()

                self.data.recipient = sp.none

                self.data.counter = 0

        sp.else:

            sp.verify(self.data.Registry.contains(exchangeAddress), ErrorMessages.InvalidExchange)

            tokenType = sp.local('tokenType',sp.bool(False))

            sp.if (self.data.Registry[exchangeAddress].token1Address == requiredTokenAddress) & (self.data.Registry[exchangeAddress].token1Id == requiredTokenId) :

                tokenType.value = self.data.Registry[exchangeAddress].token1Type

            sp.if (self.data.Registry[exchangeAddress].token2Address == requiredTokenAddress) & (self.data.Registry[exchangeAddress].token2Id == requiredTokenId):

                tokenType.value = self.data.Registry[exchangeAddress].token2Type

            SwapData = sp.record(
                tokenAmountIn = swapAmount,
                MinimumTokenOut = minimumOutput,
                recipient = sp.self_address,
                requiredTokenAddress = requiredTokenAddress,
                requiredTokenId = requiredTokenId
            )

            SwapHandle = sp.contract(
                sp.TRecord(tokenAmountIn = sp.TNat, MinimumTokenOut = sp.TNat, recipient = sp.TAddress, requiredTokenAddress = sp.TAddress, requiredTokenId = sp.TNat),
                exchangeAddress,
                "Swap"
            ).open_some()

            sp.if self.data.counter + 1 == sp.len(self.data.Route):

                SwapData = sp.record(
                    tokenAmountIn = swapAmount,
                    MinimumTokenOut = minimumOutput,
                    recipient = self.data.recipient.open_some(),
                    requiredTokenAddress = requiredTokenAddress,
                    requiredTokenId = requiredTokenId
                )

                SwapData.recipient = self.data.recipient.open_some()

                sp.transfer(SwapData, sp.mutez(0), SwapHandle)

                # Reset Params

                self.data.Lock = False

                self.data.Route = sp.map()

                self.data.recipient = sp.none

                self.data.counter = 0

            sp.else:

                SwapData = sp.record(
                    tokenAmountIn = swapAmount,
                    MinimumTokenOut = minimumOutput,
                    recipient = sp.self_address,
                    requiredTokenAddress = requiredTokenAddress,
                    requiredTokenId = requiredTokenId
                )

                sp.transfer(SwapData, sp.mutez(0), SwapHandle)

                ContractLibrary.getBalance(requiredTokenAddress,requiredTokenId, tokenType.value)


    @sp.entry_point
    def faOneCallBack(self,tokenAmount):

        sp.set_type(tokenAmount,sp.TNat)

        sp.verify(~ self.data.paused, ErrorMessages.Paused)

        sp.verify( self.data.Lock, ErrorMessages.BadState)

        sp.verify(tokenAmount > 0, ErrorMessages.ZeroBalance)

        sp.verify(sp.sender == self.data.Route[self.data.counter].requiredTokenAddress)

        sp.verify(tokenAmount >= self.data.Route[self.data.counter].minimumOutput, ErrorMessages.Slippage)

        self.data.counter += 1 

        # Call Swap 

        self.Swap(
            self.data.Route[self.data.counter].exchangeAddress, tokenAmount,
            self.data.Route[self.data.counter].requiredTokenAddress,self.data.Route[self.data.counter].requiredTokenId, self.data.Route[self.data.counter].minimumOutput)

    @sp.entry_point
    def faTwoCallBack(self,params):

        sp.set_type(params, Balance_of.response_type())

        sp.verify(~ self.data.paused, ErrorMessages.Paused)

        sp.verify( self.data.Lock, ErrorMessages.BadState)

        sp.verify(sp.sender == self.data.Route[self.data.counter].requiredTokenAddress)

        sp.verify(sp.len(params) == 1, message = "Invalid Length")
        
        balance = sp.local('balance', sp.nat(0))

        sp.for response in params: 

            sp.verify(response.request.owner == sp.self_address)

            sp.verify(response.request.token_id == self.data.Route[self.data.counter].requiredTokenId)

            balance.value = response.balance

        sp.verify(balance.value > 0, ErrorMessages.ZeroBalance)

        sp.verify(balance.value >= self.data.Route[self.data.counter].minimumOutput, ErrorMessages.Slippage)

        self.data.counter += 1

        self.Swap(
            self.data.Route[self.data.counter].exchangeAddress, balance.value,
            self.data.Route[self.data.counter].requiredTokenAddress,self.data.Route[self.data.counter].requiredTokenId,self.data.Route[self.data.counter].minimumOutput
        )


    @sp.entry_point 
    def ChangeState(self):

        """Admin function to toggle contract state
        
        UsesCases
        - Potential Exploit Detected  
        - Depreciating the Contract
        """ 

        sp.verify(self.data.adminAddress.contains(sp.sender), ErrorMessages.NotAdmin)

        self.data.paused = ~ self.data.paused

    @sp.entry_point
    def adminOperation(self,params):

        sp.set_type(params, sp.TRecord(
            address = sp.TAddress, operation = sp.TBool
        ))

        sp.verify(self.data.adminAddress.contains(sp.sender), ErrorMessages.NotAdmin)

        sp.if params.operation:

            self.data.adminAddress.add(params.address)

        sp.else:

            sp.verify(self.data.adminAddress.contains(params.address))

            self.data.adminAddress.remove(params.address)

    @sp.entry_point
    def AddExchange(self,params): 
        """
            Admin Function to add Exchange Address to the Router Contract 

            Args: 
                exchangeAddress : Exchange Address to be included in the Router 
                token1Address : token1Address of the exchange 
                token2Address : token2Address of the exchange
                token1Id : id denoting the token contract 
                token2Id : id denoting the token contract
                token1Type : Boolean type to denote FA1.2 or FA2 
                token2Type : Boolean type to denote FA1.2 or FA2 
        """

        sp.set_type(params, sp.TRecord(exchangeAddress = sp.TAddress,
         token1Address = sp.TAddress, token2Address = sp.TAddress,
         token1Id = sp.TNat, token2Id = sp.TNat, 
         token1Type = sp.TBool, token2Type = sp.TBool,
         token1Amount = sp.TNat, token2Amount = sp.TNat, userAddress = sp.TAddress, stablePair = sp.TBool
         ))

        sp.verify(self.data.adminAddress.contains(sp.sender), ErrorMessages.NotAdmin)

        sp.verify(self.data.Registry.contains(params.exchangeAddress) == False)

        self.data.Registry[params.exchangeAddress] = sp.record(
            token1Address = params.token1Address, token2Address = params.token2Address,
            token1Id  = params.token1Id, token2Id = params.token2Id,
            token1Type = params.token1Type, token2Type = params.token2Type
        )

        # Add approve for FA2 Right Away
        sp.if params.token1Type: 

            ContractLibrary.updateFaTwo(sp.self_address, params.exchangeAddress, params.token1Address, params.token1Id,True)

        sp.else:

            ContractLibrary.approveCall(params.token1Address, CONSTANT, params.exchangeAddress)

        sp.if params.token2Type: 

            ContractLibrary.updateFaTwo(sp.self_address, params.exchangeAddress, params.token2Address, params.token2Id,True)

        sp.else:

            ContractLibrary.approveCall(params.token2Address, CONSTANT, params.exchangeAddress)

        sp.if ((params.token1Amount > sp.nat(0)) & (params.token2Amount > sp.nat(0))):

            operationData = sp.record(
                token1_max = params.token1Amount, token2_max = params.token2Amount, recipient = params.userAddress
            )

            sp.if params.stablePair:

                addLiquidityHandle = sp.contract(
                    sp.TRecord(token1_max = sp.TNat, token2_max = sp.TNat, recipient = sp.TAddress),
                    params.exchangeAddress,
                    "add_liquidity"
                ).open_some()

                sp.transfer(operationData, sp.mutez(0), addLiquidityHandle)

            sp.else:

                addLiquidityHandle = sp.contract(
                    sp.TRecord(token1_max = sp.TNat, token2_max = sp.TNat, recipient = sp.TAddress),
                    params.exchangeAddress,
                    "AddLiquidity"
                ).open_some()

                sp.transfer(operationData, sp.mutez(0), addLiquidityHandle)

    @sp.entry_point
    def DeleteExchange(self,exchangeAddress): 
        """
            Admin Function to remove Exchange Address from the Router Contract 

            Args: 
                exchangeAddress : Exchange Address to be included in the Router  

            Function: 
                It will excecute a remove_operator call for the FA 2 Token Contracts 
        """

        sp.set_type(exchangeAddress, sp.TAddress)

        sp.verify(self.data.adminAddress.contains(sp.sender), ErrorMessages.NotAdmin)

        # Remove Operator
        sp.if self.data.Registry[exchangeAddress].token1Type:
            
            ContractLibrary.updateFaTwo(sp.self_address, exchangeAddress, self.data.Registry[exchangeAddress].token1Address, self.data.Registry[exchangeAddress].token1Id,False) 
        
        sp.else:

            ContractLibrary.approveCall(self.data.Registry[exchangeAddress].token1Address, sp.nat(0), exchangeAddress)
        
        sp.if self.data.Registry[exchangeAddress].token2Type: 

            ContractLibrary.updateFaTwo(sp.self_address, exchangeAddress, self.data.Registry[exchangeAddress].token2Address, self.data.Registry[exchangeAddress].token2Id,False) 

        sp.else:

            ContractLibrary.approveCall(self.data.Registry[exchangeAddress].token2Address, sp.nat(0), exchangeAddress)

        del self.data.Registry[exchangeAddress]


    @sp.entry_point
    def approveExchangeToken(self,params):

        sp.set_type(params, sp.TRecord(
            exchangeAddress = sp.TAddress,
            tokenAddress = sp.TAddress,
            tokenId = sp.TNat,
            amount = sp.TNat
        ))

        sp.verify(self.data.adminAddress.contains(sp.sender), ErrorMessages.NotAdmin)

        sp.verify(
            (
               (params.exchangeAddress == self.data.ctezFlatCurve) &
               (params.tokenAddress == self.data.ctezTokenAddress)
           ) |
            (self.data.Registry.contains(params.exchangeAddress))
        )

        sp.verify(
            (
                    (params.exchangeAddress == self.data.ctezFlatCurve) &
                    (params.tokenAddress == self.data.ctezTokenAddress)
            )  |
            (
                (params.tokenAddress == self.data.Registry[params.exchangeAddress].token1Address)
                                    &
                (params.tokenId == self.data.Registry[params.exchangeAddress].token1Id)
            ) |
            (
                (params.tokenAddress == self.data.Registry[params.exchangeAddress].token2Address)
                                    &
                (params.tokenId == self.data.Registry[params.exchangeAddress].token2Id)
            )
        )

        ContractLibrary.approveCall(params.tokenAddress, params.amount, params.exchangeAddress)           

if "templates" not in __name__:
    @sp.add_test(name = "Plenty Network Router Contract")
    def test():

        scenario = sp.test_scenario()
        scenario.h1("Plenty Network Router")

        scenario.table_of_contents()

        adminAddress = sp.test_account("adminAddress")
        ctezTokenAddress = sp.test_account("ctezTokenContract")
        ctezFlatCurveAddress = sp.test_account("ctezFlatCurveContract")

        swapRouter = Router(adminAddress.address, ctezTokenAddress.address, ctezFlatCurveAddress.address)
        scenario += swapRouter

        # token1Amount = 10**18

        # token2Amount = 10**18

        # swapRouter.AddExchange(
        #     exchangeAddress = sp.address("KT1Eh9nwGn8MPAziE7ZpyyiLShEcQfR7tyQG"),
        #     token1Address = sp.address("KT1PHbg4Dqmg9zWwuWQjo4dDTsgJ5svdyXdH"), token2Address = sp.address("KT1XL89VUosEQh5Dk9fBBwrepXBw7V4EdqL5"),
        #     token1Id = 0, token2Id = 0, 
        #     token1Type = False, token2Type = True,
        #     token1Amount = token1Amount, token2Amount = token2Amount, userAddress = adminAddress, stablePair = False
        # ).run(sender = adminAddress)

        # swapRouter.routerSwap(
        #     recipient = adminAddress,
        #     SwapAmount = 1000,
        #     Route = {
        #         0:sp.record(
        #             exchangeAddress = sp.address("KT1Eh9nwGn8MPAziE7ZpyyiLShEcQfR7tyQG"),
        #             requiredTokenAddress = sp.address("KT1XL89VUosEQh5Dk9fBBwrepXBw7V4EdqL5"),
        #             requiredTokenId = 0, 
        #             minimumOutput = 0
        #         )
        #     }
        # ).run(sender = adminAddress)

        sp.add_compilation_target(
            "PLYRouter",
            Router(adminAddress.address, ctezTokenAddress.address, ctezFlatCurveAddress.address)
        )
