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

class AMM(ContractLibrary):

    def __init__(self):

        """Initialize the contract storage
        
        Storage:
            admin: amm admin address
            token1Address: contract address for first token used in the amm
            token1Id: token id for first token used in the amm
            token1Check: boolean describing whether first token used in the amm is FA2
            token2Address: contract address for second token used in the amm
            token2Id: token id for second token used in the amm
            token2Check: boolean describing whether second token used in the amm is FA2
            lpTokenAddress: contract address for the LP tokens used in the amm
            lpFee: % fee for the LP
            state: Boolean Value for switching between normal fees and Ve System
            voterContract : voter contract for Ve System
            token1_pool: total liquidity of token 1
            token2_pool: total liquidity of token 2
            totalSupply: total supply of LP tokens
            paused: boolean describing whether contract is paused
            token1_Fee: total system fee accumulated in token 1
            token2_Fee: total system fee accumulated in token 2
            maxSwapLimit: max % of total liquidity that can be swapped in one go
        """

        self.init_type(
            sp.TRecord(
            admin = sp.TAddress, 
            token1Address = sp.TAddress, 
            token1Id = sp.TNat,
            token1Check = sp.TBool,
            token2Address = sp.TAddress,
            token2Id = sp.TNat,
            token2Check = sp.TBool,
            lpTokenAddress = sp.TAddress,
            lpFee = sp.TNat,
            state = sp.TBool,
            voterContract = sp.TOption(sp.TAddress),
            token1_pool = sp.TNat, 
            token2_pool = sp.TNat, 
            totalSupply = sp.TNat,
            paused = sp.TBool,
            token1_Fee = sp.TNat, 
            token2_Fee = sp.TNat,
            maxSwapLimit = sp.TNat,
            )
        )


    @sp.entry_point
    def Swap(self,params): 
        """ Function for Users to Swap their assets to get the required Token 
        
        Args:
            tokenAmountIn: amount of tokens sent by user that needs to be swapped
            MinimumTokenOut: minimum amount of token expected by user after swap 
            recipient: address that will receive the swapped out tokens 
            requiredTokenAddress: contract address of the token that is expected to be returned after swap
            requiredTokenId: id of the token that is expected to be returned after swap
        """

        sp.set_type(params, sp.TRecord(tokenAmountIn = sp.TNat, MinimumTokenOut = sp.TNat, recipient = sp.TAddress, requiredTokenAddress = sp.TAddress, requiredTokenId = sp.TNat))

        sp.verify( ~self.data.paused,"Plenty_Network_Paused_State")

        sp.verify( ( (params.requiredTokenAddress == self.data.token1Address) & (params.requiredTokenId == self.data.token1Id)) | 
        ( (params.requiredTokenAddress == self.data.token2Address)  & (params.requiredTokenId == self.data.token2Id)),"Plenty_Network_Invalid_Pair")

        requiredTokenAmount = sp.local('requiredTokenAmount', sp.nat(0))
        SwapTokenPool = sp.local('SwapTokenPool', sp.nat(0))

        lpfee = sp.local('lpfee', sp.nat(0))

        tokenTransfer = sp.local('tokenTransfer', sp.nat(0))

        sp.if (params.requiredTokenAddress == self.data.token1Address) & (params.requiredTokenId == self.data.token1Id): 

            requiredTokenAmount.value = self.data.token2_pool
            SwapTokenPool.value = self.data.token1_pool

        sp.else: 

            requiredTokenAmount.value = self.data.token1_pool
            SwapTokenPool.value = self.data.token2_pool

        sp.verify(params.tokenAmountIn * 100 <= requiredTokenAmount.value * self.data.maxSwapLimit,"Plenty_Network_Swap_Limit_Exceed")

        lpfee.value = params.tokenAmountIn / self.data.lpFee

        Invariant = sp.local('Invariant', self.data.token1_pool * self.data.token2_pool)

        Invariant.value = Invariant.value / sp.as_nat( (requiredTokenAmount.value + params.tokenAmountIn) - lpfee.value )

        tokenTransfer.value = sp.as_nat(SwapTokenPool.value - Invariant.value)

        sp.verify(tokenTransfer.value >= params.MinimumTokenOut,"Plenty_Network_Higher_Slippage")

        sp.verify(lpfee.value > 0,"Plenty_Network_Zero_System_Fee")

        sp.if (params.requiredTokenAddress == self.data.token1Address) & (params.requiredTokenId == self.data.token1Id): 

            self.data.token1_pool = Invariant.value

            sp.if self.data.state:

                self.data.token2_pool += sp.as_nat(params.tokenAmountIn - lpfee.value)
                self.data.token2_Fee += lpfee.value

            sp.else:

                self.data.token2_pool += params.tokenAmountIn

            # Transfer tokens to Exchange
            ContractLibrary.TransferToken(sp.sender, sp.self_address, params.tokenAmountIn, self.data.token2Address, self.data.token2Id, self.data.token2Check)

            # Transfer tokens to the recipient 
            ContractLibrary.TransferToken(sp.self_address, params.recipient, tokenTransfer.value, self.data.token1Address, self.data.token1Id, self.data.token1Check)

        sp.else: 

            self.data.token2_pool = Invariant.value

            sp.if self.data.state:

                self.data.token1_pool += sp.as_nat(params.tokenAmountIn - lpfee.value)
                self.data.token1_Fee += lpfee.value

            sp.else:

                self.data.token1_pool += params.tokenAmountIn

            # Transfer Tokens to Exchange
            ContractLibrary.TransferToken(sp.sender, sp.self_address, params.tokenAmountIn, self.data.token1Address, self.data.token1Id, self.data.token1Check)

            # Transfer Tokens to the recipient
            ContractLibrary.TransferToken(sp.self_address, params.recipient, tokenTransfer.value, self.data.token2Address, self.data.token2Id, self.data.token2Check)

    @sp.entry_point 
    def AddLiquidity(self,params): 
        """Allows users to add liquidity to the pool and gain LP tokens
        
        Args:
            token1_max: max amount of token 1 that the user wants to supply to the pool 
            token2_max: max amount of token 2 that the user wants to supply to the pool 
            recipient: account address that will be credited with the LP tokens
        """

        sp.set_type(params, sp.TRecord(token1_max = sp.TNat, token2_max = sp.TNat, recipient = sp.TAddress))
        
        token1Amount = sp.local('token1Amount', sp.nat(0))

        token2Amount = sp.local('token2Amount', sp.nat(0))

        liquidity = sp.local('liquidity', sp.nat(0))

        sp.if self.data.totalSupply != sp.nat(0): 

            sp.if (params.token1_max * self.data.token2_pool) / self.data.token1_pool <= params.token2_max: 

                token1Amount.value = params.token1_max

                token2Amount.value = (params.token1_max * self.data.token2_pool ) / self.data.token1_pool

                
            sp.if (params.token2_max * self.data.token1_pool) / self.data.token2_pool <= params.token1_max: 

                token2Amount.value = params.token2_max

                token1Amount.value = (params.token2_max * self.data.token1_pool) / self.data.token2_pool

            sp.verify(token1Amount.value > 0, "Plenty_Network_Invalid_LP_Ratio")

            sp.verify(token2Amount.value > 0, "Plenty_Network_Invalid_LP_Ratio")
            
            sp.if ( token1Amount.value * self.data.totalSupply ) / self.data.token1_pool < ( token2Amount.value * self.data.totalSupply) / self.data.token2_pool: 

                liquidity.value = ( token1Amount.value * self.data.totalSupply ) / self.data.token1_pool

            sp.else: 

                liquidity.value = ( token2Amount.value * self.data.totalSupply) / self.data.token2_pool
            
        sp.else: 

            # Value = sp.local('Value',params.token1_max * params.token2_max )
            
            sqrt = sp.local( 'sqrt' , self.square_root( params.token1_max * params.token2_max ) )

            sp.verify(sqrt.value > INITIAL_LIQUIDITY , "Negative_Val" )

            liquidity.value = abs( sqrt.value - INITIAL_LIQUIDITY )
            
            self.data.totalSupply += INITIAL_LIQUIDITY

            token1Amount.value = params.token1_max

            token2Amount.value = params.token2_max
            

        sp.verify(liquidity.value > 0 )

        sp.verify(token1Amount.value <= params.token1_max )

        sp.verify(token2Amount.value <= params.token2_max )
        
        # Transfer Funds to Exchange 
        
        ContractLibrary.TransferToken(sp.sender, sp.self_address, token1Amount.value, self.data.token1Address, self.data.token1Id, self.data.token1Check)

        ContractLibrary.TransferToken(sp.sender, sp.self_address, token2Amount.value, self.data.token2Address, self.data.token2Id, self.data.token2Check)

        self.data.token1_pool += token1Amount.value

        self.data.token2_pool += token2Amount.value

        # Mint LP Tokens
        self.data.totalSupply += liquidity.value

        mintParam = sp.record(
            address = params.recipient, 
            value = liquidity.value
        )

        mintHandle = sp.contract(
            sp.TRecord(address = sp.TAddress, value = sp.TNat),
            self.data.lpTokenAddress,
            "mint"
            ).open_some()

        sp.transfer(mintParam, sp.mutez(0), mintHandle)

    @sp.entry_point 
    def RemoveLiquidity(self,params): 
        """Allows users to remove their liquidity from the pool by burning their LP tokens
        
        Args:
            lpAmount: amount of LP tokens to be burned
            token1_min: minimum amount of token 1 expected by the user upon burning given LP tokens
            token2_min: minimum amount of token 2 expected by the user upon burning given LP tokens 
            recipient: account address that will be credited with the tokens removed from the pool
        """  

        sp.set_type(params, sp.TRecord(lpAmount = sp.TNat ,token1_min = sp.TNat, token2_min = sp.TNat, recipient = sp.TAddress))
        
        sp.verify(self.data.totalSupply != sp.nat(0),"Plenty_Network_Not_Initialized")

        sp.verify(params.lpAmount <= self.data.totalSupply,"Plenty_Network_Insufficient_Balance")
        
        token1Amount = sp.local('token1Amount', sp.nat(0))

        token2Amount = sp.local('token2Amount', sp.nat(0))

        # Computing the Tokens and Plenty Provided for removing Liquidity

        token1Amount.value = (params.lpAmount * self.data.token1_pool) / self.data.totalSupply

        token2Amount.value = (params.lpAmount * self.data.token2_pool) / self.data.totalSupply

        # Values should be greater than  Minimum threshold  

        sp.verify(token1Amount.value >= params.token1_min)

        sp.verify(token2Amount.value >= params.token2_min)

        # Subtracting Values  

        self.data.token1_pool = sp.as_nat( self.data.token1_pool - token1Amount.value )

        self.data.token2_pool = sp.as_nat( self.data.token2_pool - token2Amount.value )

        self.data.totalSupply = sp.as_nat( self.data.totalSupply - params.lpAmount )
        
        # Burning LP Tokens  
        
        burnParam = sp.record(
            address = sp.sender, 
            value = params.lpAmount
        )

        burnHandle = sp.contract(
            sp.TRecord(address = sp.TAddress, value = sp.TNat),
            self.data.lpTokenAddress,
            "burn"
            ).open_some()

        sp.transfer(burnParam, sp.mutez(0), burnHandle)

        # Sending Plenty and Tokens 

        ContractLibrary.TransferToken(sp.self_address, params.recipient, token1Amount.value, self.data.token1Address, self.data.token1Id, self.data.token1Check)

        ContractLibrary.TransferToken(sp.self_address, params.recipient, token2Amount.value, self.data.token2Address, self.data.token2Id, self.data.token2Check)

    @sp.entry_point 
    def ModifyFee(self,lpFee):

        """Admin function to modify the LP Fees
        
        Max Fee can be 2% Hardcoded

        Args:
            lpFee: new % fee for the liquidity providers
        """ 

        sp.set_type(lpFee, sp.TNat)

        sp.verify(sp.sender == self.data.admin,"Plenty_Network_Not_Admin")

        sp.verify( lpFee > 50)

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
        """Admin function to toggle contract state
        
        UsesCases

        - In case of Rug Pull by a certain Token 
        - Potential Exploit Detected  
        - Depreciating the Contract

        """ 

        sp.verify(sp.sender == self.data.admin,"Plenty_Network_Not_Admin")

        self.data.paused = ~ self.data.paused

    @sp.entry_point
    def ChangeAdmin(self,adminAddress): 
        """Admin function to Update Admin Address
        
        Args:
            adminAddress: Upgrades adminAddress to new MultiSig or DAO 
        """ 

        sp.set_type(adminAddress, sp.TAddress)

        sp.verify(sp.sender == self.data.admin,"Plenty_Network_Not_Admin")

        self.data.admin = adminAddress

    @sp.entry_point 
    def ModifyMaxSwapAmount(self,amount): 
        """Admin function to modify the max swap limit
        
        Args:
            amount: new max % of total liquidity that can be swapped
        """ 
        sp.set_type(amount,sp.TNat)

        sp.verify(sp.sender == self.data.admin,"Plenty_Network_Not_Admin")

        self.data.maxSwapLimit = amount

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

        sp.if self.data.token1_Fee != sp.nat(0): 

            ContractLibrary.TransferToken(sp.self_address, params.feeDistributor, self.data.token1_Fee, self.data.token1Address, self.data.token1Id, self.data.token1Check )
            
        sp.if self.data.token2_Fee != sp.nat(0): 

            ContractLibrary.TransferToken(sp.self_address, params.feeDistributor, self.data.token2_Fee, self.data.token2Address, self.data.token2Id, self.data.token2Check )

        # Call the feeDistributor contract

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


        sp.if self.data.token1Check:

            fees_map.value[sp.variant("fa2", (self.data.token1Address, self.data.token1Id))] = self.data.token1_Fee

        sp.else:

            fees_map.value[sp.variant("fa12", self.data.token1Address)] = self.data.token1_Fee


        sp.if self.data.token2Check:

            fees_map.value[sp.variant("fa2", (self.data.token2Address, self.data.token2Id))] = self.data.token2_Fee

        sp.else:

            fees_map.value[sp.variant("fa12", self.data.token2Address)] = self.data.token2_Fee

        c = sp.contract(ADD_FEES_PARAMS, params.feeDistributor, "add_fees").open_some()
        sp.transfer(
            sp.record(
                epoch=params.epoch,
                fees=fees_map.value
            ),
            sp.tez(0),
            c,
        )

        self.data.token1_Fee = sp.nat(0)

        self.data.token2_Fee = sp.nat(0)
    

    @sp.onchain_view()
    def getReserveBalance(self,params): 

        """View function to get the current AMM Liquidity reserve
        
        Args:
            token1Address: contract address for first token used in the amm
            token1Id: token id for first token used in the amm
            token2Address: contract address for second token used in the amm
            token2Id: token id for second token used in the amm
        Returns:
            sp.TRecord(token1_pool=sp.TNat, token2_pool=sp.TNat): total liquidity for token 1 and token 2 present in the pool
        """

        sp.set_type(params, sp.TRecord(token1Address = sp.TAddress, token1Id = sp.TNat,token2Address = sp.TAddress, token2Id = sp.TNat))

        sp.verify( ( (params.token1Address == self.data.token1Address) & (params.token1Id == self.data.token1Id)) &
        ( (params.token2Address == self.data.token2Address)  & (params.token2Id == self.data.token2Id)))
        
        reserve = sp.record(    
            token1_pool = self.data.token1_pool, 
            token2_pool = self.data.token2_pool
        )

        sp.result(reserve)

    @sp.onchain_view()
    def getExchangeFee(self,params): 

        """
            View function to get the Fee Percentage for Liquidity Providers and System Fee
            
            In order to get Percentage, 1/feeValue * 100 = feeValue Percentage

        Args:
            token1Address: contract address for first token used in the amm
            token1Id: token id for first token used in the amm
            token2Address: contract address for second token used in the amm
            token2Id: token id for second token used in the amm

        Returns:
            sp.TRecord(systemFee = sp.TNat, lpFee = sp.TNat): current system fee and lp fee for the amm
        """

        sp.set_type(params, sp.TRecord(token1Address = sp.TAddress, token1Id = sp.TNat,token2Address = sp.TAddress, token2Id = sp.TNat))

        sp.verify( ( (params.token1Address == self.data.token1Address) & (params.token1Id == self.data.token1Id)) &
        ( (params.token2Address == self.data.token2Address)  & (params.token2Id == self.data.token2Id)))

        sp.result(sp.record(token1Fee = self.data.token1_Fee, token2Fee = self.data.token2_Fee))


