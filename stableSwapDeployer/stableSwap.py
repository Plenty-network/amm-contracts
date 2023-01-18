import smartpy as sp 

INITIAL_LIQUIDITY = 1000

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

        
    @sp.private_lambda(wrap_call=True)
    def square_root(self , x): 
        """Calculates the square root of a given integer
        
        Args:
            x : integer whose square root is to be determined
        Returns:
            square root of x
        """

        sp.verify(x >= 0,"Negative_Value")
        
        y = sp.local('y', x)
        
        sp.while y.value * y.value > x:
        
            y.value = (x // y.value + y.value) // 2
        
        sp.verify((y.value * y.value <= x) & (x < (y.value + 1) * (y.value + 1)))

        sp.result(y.value)

class FlatCurve(ContractLibrary):

    def __init__(self):

        self.init_type(
            sp.TRecord(
                token1Pool= sp.TNat, 
                token2Pool= sp.TNat, 
                token1Id= sp.TNat, 
                token2Id= sp.TNat,
                token1Check= sp.TBool, token2Check= sp.TBool, 
                token1Precision= sp.TNat, token2Precision= sp.TNat,
                token1Address = sp.TAddress, token2Address= sp.TAddress,
                token1Fee = sp.TNat, token2Fee = sp.TNat, state = sp.TBool, voterContract= sp.TOption(sp.TAddress),
                lqtTotal= sp.TNat, lpFee= sp.TNat, lqtAddress= sp.TAddress, admin = sp.TAddress, paused = sp.TBool
            )
        )

    def burn(self,burnData):
        c = sp.contract(sp.TRecord(address = sp.TAddress, value = sp.TNat), self.data.lqtAddress, entry_point="burn").open_some()
        sp.transfer(burnData,sp.mutez(0),c)

    def mint(self,mintData):
        c = sp.contract(sp.TRecord(address = sp.TAddress, value = sp.TNat), self.data.lqtAddress, entry_point="mint").open_some()
        sp.transfer(mintData,sp.mutez(0),c)
    
    def util(self, x, y):
        sp.set_type(x, sp.TNat)
        sp.set_type(y, sp.TNat)
        plus = x + y
        minus = x - y
        plus_2 = plus * plus 
        plus_4 = plus_2 *plus_2
        plus_8 = plus_4 * plus_4
        plus_7 = plus_4 * plus_2 * plus 
        minus_2 = minus * minus
        minus_4 = minus_2 * minus_2
        minus_8 = minus_4 * minus_4
        minus_7 = minus_4 * minus_2 * minus
        return sp.record(first=abs(sp.to_int(plus_8) - minus_8), second = 8 * abs(minus_7 + sp.to_int(plus_7)))

    def newton(self, params):
        rounds = sp.local('rounds', params.n)
        dy = sp.local('dy', params.dy)
        new_util = sp.local('new_util', self.util((params.x+params.dx), abs(params.y - dy.value)))
        new_u = sp.local('new_u', new_util.value.first)
        new_du_dy = sp.local('new_du_dy', new_util.value.second)
        sp.while rounds.value != 0:
            new_util.value = self.util((params.x+params.dx), abs(params.y - dy.value))
            new_u.value = new_util.value.first
            new_du_dy.value = new_util.value.second
            dy.value = dy.value + (abs(new_u.value - params.u) / new_du_dy.value)
            rounds.value = rounds.value - 1
        return dy.value

    def newton_dx_to_dy(self, params):
        sp.set_type(params,sp.TRecord(x = sp.TNat, y = sp.TNat, dx = sp.TNat, rounds = sp.TInt))
        utility = self.util(params.x, params.y)
        u = utility.first
        dy = self.newton(sp.record(x = params.x, y = params.y, dx = params.dx, dy = sp.nat(0), u = u, n = params.rounds))
        return dy
    
    @sp.entry_point 
    def add_liquidity(self,params): 
        """Allows users to add liquidity to the pool and gain LP tokens
        
        Args:
            token1_max: max amount of token1 that the user wants to supply to the pool 
            token2_max: max amount of token2 that the user wants to supply to the pool 
            recipient: account address that will be credited with the LP tokens
        """
        sp.set_type(params, sp.TRecord(token1_max = sp.TNat, token2_max = sp.TNat, recipient = sp.TAddress))
        token1Amount = sp.local('token1Amount', sp.nat(0))
        token2Amount = sp.local('token2Amount', sp.nat(0))
        liquidity = sp.local('liquidity', sp.nat(0))
        sp.if self.data.lqtTotal != sp.nat(0): 
            sp.if (params.token1_max * self.data.token2Pool) / self.data.token1Pool <= params.token2_max: 
                token1Amount.value = params.token1_max
                token2Amount.value = (params.token1_max * self.data.token2Pool ) / self.data.token1Pool
            sp.if (params.token2_max * self.data.token1Pool) / self.data.token2Pool <= params.token1_max: 
                token2Amount.value = params.token2_max
                token1Amount.value = (params.token2_max * self.data.token1Pool) / self.data.token2Pool
            sp.verify(token1Amount.value > 0, "Plenty_Network_Invalid_LP_Ratio")
            sp.verify(token2Amount.value > 0, "Plenty_Network_Invalid_LP_Ratio")

            sp.if ( token1Amount.value * self.data.lqtTotal ) / self.data.token1Pool < ( token2Amount.value * self.data.lqtTotal) / self.data.token2Pool: 
                liquidity.value = ( token1Amount.value * self.data.lqtTotal ) / self.data.token1Pool
            sp.else: 
                liquidity.value = ( token2Amount.value * self.data.lqtTotal) / self.data.token2Pool
        sp.else: 
            
            sp.verify(params.token1_max*self.data.token1Precision == params.token2_max*self.data.token2Precision, "Plenty_Network_Invalid_LP_Ratio")

            sqrt = sp.local( 'sqrt' , 2 * self.square_root( params.token1_max * params.token2_max ) )

            sp.verify(sqrt.value > INITIAL_LIQUIDITY , "Negative_Val" )
            
            liquidity.value = abs(sqrt.value - INITIAL_LIQUIDITY )
            
            self.data.lqtTotal += 1000

            token1Amount.value = params.token1_max
            token2Amount.value = params.token2_max
            
        sp.verify(liquidity.value > 0 )
        sp.verify(token1Amount.value <= params.token1_max )
        sp.verify(token2Amount.value <= params.token2_max )

        # Transfer Funds to Exchange 
        ContractLibrary.TransferToken(sp.sender, sp.self_address, token1Amount.value, self.data.token1Address, self.data.token1Id, self.data.token1Check)
        ContractLibrary.TransferToken(sp.sender, sp.self_address, token2Amount.value, self.data.token2Address, self.data.token2Id, self.data.token2Check)

        self.data.token1Pool += token1Amount.value
        self.data.token2Pool += token2Amount.value

        # Mint LP Tokens
        self.data.lqtTotal += liquidity.value
        self.mint(sp.record(address=params.recipient, value = liquidity.value))

    @sp.entry_point 
    def remove_liquidity(self,params): 
        """Allows users to remove their liquidity from the pool by burning their LP tokens
        
        Args:
            lpAmount: amount of LP tokens to be burned
            token1_min: minimum amount of token1 expected by the user upon burning given LP tokens
            token2_min: minimum amount of token2 expected by the user upon burning given LP tokens
            recipient: address of the user that will get the tokens
        """
        sp.set_type(params, sp.TRecord(lpAmount = sp.TNat ,token1_min = sp.TNat, token2_min = sp.TNat, recipient = sp.TAddress))
        sp.verify(self.data.lqtTotal != sp.nat(0),"Plenty_Network_Not_Initialized")
        sp.verify(params.lpAmount <= self.data.lqtTotal,"Plenty_Network_Insufficient_Balance")

        token1Amount = sp.local('token1Amount', sp.nat(0))
        token2Amount = sp.local('token2Amount', sp.nat(0))

        token1Amount.value = (params.lpAmount * self.data.token1Pool) / self.data.lqtTotal
        token2Amount.value = (params.lpAmount * self.data.token2Pool) / self.data.lqtTotal
        sp.verify(token1Amount.value >= params.token1_min)
        sp.verify(token2Amount.value >= params.token2_min)

        # Subtracting Values  
        self.data.token1Pool = sp.as_nat(self.data.token1Pool - token1Amount.value)
        self.data.token2Pool = sp.as_nat(self.data.token2Pool - token2Amount.value)  
        self.data.lqtTotal = sp.as_nat(self.data.lqtTotal - params.lpAmount)
        
        # Burning LP Tokens  
        self.burn(sp.record(address=sp.sender, value= params.lpAmount))

        # Sending Tokens 
        ContractLibrary.TransferToken(sp.self_address, params.recipient, token1Amount.value, self.data.token1Address, self.data.token1Id, self.data.token1Check)
        ContractLibrary.TransferToken(sp.self_address, params.recipient, token2Amount.value, self.data.token2Address, self.data.token2Id, self.data.token2Check)

    @sp.entry_point
    def Swap(self,params):
        """ Function for Users to Swap their assets to get the required Token 
        
        Args:
            tokenAmountIn: amount of tokens sent by user that needs to be swapped
            minTokenOut: minimum amount of token expected by user after swap 
            recipient: address that will receive the swapped out tokens 
            requiredTokenAddress: contract address of the token that is expected to be returned after swap
            requiredTokenId: id of the token that is expected to be returned after swap
        """
        sp.set_type(params, sp.TRecord(tokenAmountIn = sp.TNat, MinimumTokenOut = sp.TNat, recipient = sp.TAddress, requiredTokenAddress = sp.TAddress, requiredTokenId = sp.TNat))
        sp.verify(~self.data.paused, "Plenty_Network_Paused_State")
        sp.verify(params.tokenAmountIn >sp.nat(0),"Plenty_Network_Zero_Swap")
        sp.verify(((params.requiredTokenAddress == self.data.token1Address) & (params.requiredTokenId == self.data.token1Id)) | 
        ((params.requiredTokenAddress == self.data.token2Address) & (params.requiredTokenId == self.data.token2Id)),"Plenty_Network_Invalid_Pair")

        token1PoolNew = sp.local("token1PoolNew", self.data.token1Pool * self.data.token1Precision)
        token2PoolNew = sp.local("token2PoolNew", self.data.token2Pool * self.data.token2Precision)

        sp.if (params.requiredTokenAddress == self.data.token1Address) & (params.requiredTokenId == self.data.token1Id): 
            tokenBoughtWithoutFee = self.newton_dx_to_dy(sp.record(x = token2PoolNew.value, y = token1PoolNew.value, dx = params.tokenAmountIn * self.data.token2Precision, rounds = 5))
            fee = sp.local("fee", tokenBoughtWithoutFee/self.data.lpFee)
            tokenBought = abs(tokenBoughtWithoutFee - fee.value) / self.data.token1Precision

            sp.verify(tokenBought>=params.MinimumTokenOut, "Plenty_Network_Min_Cash_Error")
            sp.verify(tokenBought<self.data.token1Pool, "Plenty_Network_Cash_Bought_Exceeds_Pool")

            sp.if self.data.state:

                self.data.token1Pool = sp.as_nat(self.data.token1Pool - tokenBoughtWithoutFee/self.data.token1Precision)
                self.data.token1Fee += fee.value / self.data.token1Precision

            sp.else:

                self.data.token1Pool= abs(self.data.token1Pool - tokenBought)

            self.data.token2Pool += params.tokenAmountIn

            ContractLibrary.TransferToken(sp.sender, sp.self_address, params.tokenAmountIn, self.data.token2Address, self.data.token2Id, self.data.token2Check)
            ContractLibrary.TransferToken(sp.self_address, params.recipient, tokenBought, self.data.token1Address, self.data.token1Id, self.data.token1Check)

        sp.else :

            tokenBoughtWithoutFee = self.newton_dx_to_dy(sp.record(x = token1PoolNew.value, y = token2PoolNew.value, dx = params.tokenAmountIn * self.data.token1Precision, rounds = 5))
            fee = sp.local("fee", tokenBoughtWithoutFee/self.data.lpFee)
            tokenBought = abs(tokenBoughtWithoutFee - fee.value) / self.data.token2Precision

            sp.verify(tokenBought>=params.MinimumTokenOut, "Plenty_Network_Min_Cash_Error")
            sp.verify(tokenBought<self.data.token2Pool, "Plenty_Network_Cash_Bought_Exceeds_Pool")

            sp.if self.data.state:

                self.data.token2Pool = sp.as_nat(self.data.token2Pool - tokenBoughtWithoutFee/self.data.token2Precision)
                self.data.token2Fee += fee.value / self.data.token2Precision

            sp.else:

                self.data.token2Pool= sp.as_nat(self.data.token2Pool - tokenBought)

            self.data.token1Pool= self.data.token1Pool + params.tokenAmountIn

            ContractLibrary.TransferToken(sp.sender, sp.self_address, params.tokenAmountIn, self.data.token1Address, self.data.token1Id, self.data.token1Check)
            ContractLibrary.TransferToken(sp.self_address, params.recipient, tokenBought, self.data.token2Address, self.data.token2Id, self.data.token2Check)
    
    @sp.entry_point
    def ModifyFee(self,lpFee):

        """Admin function to modify the LP Fees
        Max Fee can be 1% Hardcoded
        Args:
            lpFee: new % fee for the liquidity providers
        """

        sp.set_type(lpFee, sp.TNat)

        sp.verify(sp.sender == self.data.admin,"Plenty_Network_Not_Admin")

        sp.verify( lpFee >= 100)

        self.data.lpFee = lpFee


    @sp.entry_point
    def ChangeSystem(self,newVoterContract):

        """
            Admin function for executing transition to Ve System
            This is a one-way change
        """

        sp.set_type(newVoterContract, sp.TAddress)

        sp.verify(sp.sender == self.data.admin,"Plenty_Network_Not_Admin")

        self.data.voterContract = sp.some(newVoterContract)

        self.data.state = True

    @sp.entry_point 
    def ChangeState(self):
        sp.verify(sp.sender == self.data.admin,"Plenty_Network_Not_Admin")
        self.data.paused = ~ self.data.paused

    @sp.entry_point
    def ChangeAdmin(self,adminAddress): 
        sp.set_type(adminAddress, sp.TAddress)
        sp.verify(sp.sender == self.data.admin,"Plenty_Network_Not_Admin")
        self.data.admin = adminAddress

    @sp.entry_point
    def forwardFee(self,params):

        """Admin function to withdraw lp Fees for the Ve System
        Args:
            feeDistributor: account address where the lp fees will be transferred to fee distributor contract
            epoch:
        """

        sp.set_type(params, sp.TRecord(feeDistributor=sp.TAddress, epoch=sp.TNat))

        sp.verify(self.data.state,"Plenty_Network_Invalid_State")

        sp.verify(sp.sender == self.data.voterContract.open_some(),"Plenty_Network_Not_Voter")

        sp.if self.data.token1Fee != sp.nat(0):

            ContractLibrary.TransferToken(sp.self_address, params.feeDistributor, self.data.token1Fee, self.data.token1Address, self.data.token1Id, self.data.token1Check)

        sp.if self.data.token2Fee != sp.nat(0):

            ContractLibrary.TransferToken(sp.self_address, params.feeDistributor, self.data.token2Fee, self.data.token2Address, self.data.token2Id, self.data.token2Check)

        # Type constants for FeeDistributor call
        TOKEN_VARIANT = sp.TVariant(
            fa12=sp.TAddress,
            fa2=sp.TPair(sp.TAddress, sp.TNat),
            tez=sp.TUnit,
        )

        ADD_FEES_PARAMS = sp.TRecord(
            epoch=sp.TNat,
            fees=sp.TMap(TOKEN_VARIANT, sp.TNat),
        ).layout(("epoch", "fees"))

        fees_map = sp.local("fees_map", sp.map(l={}, tkey=TOKEN_VARIANT, tvalue=sp.TNat))

        # Record token 1 fees
        sp.if self.data.token1Check:
            fees_map.value[sp.variant("fa2", (self.data.token1Address, self.data.token1Id))] = self.data.token1Fee
        sp.else:
            fees_map.value[sp.variant("fa12", self.data.token1Address)] = self.data.token1Fee
        
        # Record token 2 fees
        sp.if self.data.token2Check:
            fees_map.value[sp.variant("fa2", (self.data.token2Address, self.data.token2Id))] = self.data.token2Fee
        sp.else:
            fees_map.value[sp.variant("fa12", self.data.token2Address)] = self.data.token2Fee
 
        # Call FeeDistributor to record the fees for the epoch
        c = sp.contract(ADD_FEES_PARAMS, params.feeDistributor, "add_fees").open_some()
        sp.transfer(
            sp.record(
                epoch=params.epoch, 
                fees=fees_map.value
            ),
            sp.tez(0),
            c,
        )

        self.data.token1Fee = 0

        self.data.token2Fee = 0

    @sp.onchain_view()
    def getReserveBalance(self): 
        reserve = sp.record(
            token1Pool = self.data.token1Pool, 
            token2Pool = self.data.token2Pool
        )
        sp.result(reserve)