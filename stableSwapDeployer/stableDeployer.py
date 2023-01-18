import smartpy as sp

stableSwap = sp.io.import_script_from_url("file:./stableSwapDeployer/stableSwap.py")

class stableFactoryContract(sp.Contract):

    def __init__(self, _adminAddress):

        self.stableSwap = stableSwap.FlatCurve()

        self.init(
            adminAddress = _adminAddress,
            lpFee = sp.nat(2000),
            lpDeployer = _adminAddress,
            routerAddress = _adminAddress,
            Registry = sp.big_map(
                tvalue = sp.TRecord(token1Address = sp.TAddress, token2Address = sp.TAddress, lpTokenAddress = sp.TAddress,
                token1Id = sp.TNat, token2Id = sp.TNat,
                token1Type = sp.TBool, token2Type = sp.TBool,
                token1Precision = sp.TNat, token2Precision = sp.TNat
                ),
                tkey = sp.TAddress
            ),
            lpMapping = sp.big_map(
                tvalue = sp.TAddress,
                tkey = sp.TAddress
            )
        )

    @sp.entry_point
    def deployPair(self, params):

        sp.set_type(params, sp.TRecord(
            token1Address = sp.TAddress, token1Id = sp.TNat, token1Type = sp.TBool, token1Precision = sp.TNat, token1Amount = sp.TNat,
            token2Address = sp.TAddress, token2Id = sp.TNat, token2Type = sp.TBool, token2Precision = sp.TNat, token2Amount = sp.TNat,
            lpTokenAddress = sp.TAddress, userAddress = sp.TAddress
        ))

        sp.verify(sp.sender == self.data.lpDeployer)

        ammAddress = sp.some(
            sp.create_contract(
                storage = sp.record(
                    token1Pool= sp.nat(0), 
                    token2Pool= sp.nat(0), 
                    token1Id= params.token1Id, 
                    token2Id= params.token2Id,
                    token1Check= params.token1Type, token2Check= params.token2Type, 
                    token1Precision= params.token1Precision, token2Precision= params.token2Precision,
                    token1Address = params.token1Address, token2Address= params.token2Address,
                    token1Fee = sp.nat(0), token2Fee = sp.nat(0), state = False , voterContract= sp.none,
                    lqtTotal= sp.nat(0), lpFee= self.data.lpFee, lqtAddress= params.lpTokenAddress, admin = self.data.adminAddress, paused = False
                ),
                contract = self.stableSwap
            )
        )

        sp.emit(
            sp.record(
                token1Address = params.token1Address,
                token2Address = params.token2Address,
                lpTokenAddress = params.lpTokenAddress,
                token1Id = params.token1Id,
                token2Id = params.token2Id, 
                token1Type = params.token1Type,
                token2Type = params.token2Type,
                token1Precision = params.token1Precision, 
                token2Precision = params.token2Precision,
                exchangeAddress = ammAddress.open_some()
            )
        )

        self.data.Registry[ammAddress.open_some()] = sp.record(
            token1Address = params.token1Address,
            token2Address = params.token2Address,
            lpTokenAddress = params.lpTokenAddress,
            token1Id = params.token1Id,
            token2Id = params.token2Id, 
            token1Type = params.token1Type,
            token2Type = params.token2Type,
            token1Precision = params.token1Precision, 
            token2Precision = params.token2Precision,
        )

        contractHandle = sp.contract(
                sp.TAddress,
                params.lpTokenAddress,
                "updateExchangeAddress"
            ).open_some()

        sp.transfer(ammAddress.open_some(), sp.mutez(0), contractHandle)

        # Add Pair to the Router
        self.routerCall(
                ammAddress.open_some(),
                params.token1Address,
                params.token2Address,
                params.token1Id,
                params.token2Id,
                params.token1Type,
                params.token2Type,
                params.token1Amount,
                params.token2Amount,
                params.userAddress
        )

        self.data.lpMapping[params.lpTokenAddress] = ammAddress.open_some()

    @sp.entry_point
    def addExistingPair(self, params):

        sp.set_type(
            params, sp.TRecord(
                token1Address = sp.TAddress, token1Id = sp.TNat, token1Type = sp.TBool, token1Precision = sp.TNat,
                token2Address = sp.TAddress, token2Id = sp.TNat, token2Type = sp.TBool, token2Precision = sp.TNat,
                lpTokenAddress = sp.TAddress, exchangeAddress = sp.TAddress,
                routerCall = sp.TBool
            )
        )

        sp.verify( (sp.sender == self.data.adminAddress) |  (sp.sender == self.data.lpDeployer))

        self.data.Registry[params.exchangeAddress] = sp.record(
            token1Address = params.token1Address,
            token2Address = params.token2Address,
            lpTokenAddress = params.lpTokenAddress,
            token1Id = params.token1Id,
            token2Id = params.token2Id, 
            token1Type = params.token1Type,
            token2Type = params.token2Type,
            token1Precision = params.token1Precision, 
            token2Precision = params.token2Precision
        )

        sp.if params.routerCall:

            self.routerCall(
                params.exchangeAddress,
                params.token1Address,
                params.token2Address,
                params.token1Id,
                params.token2Id,
                params.token1Type,
                params.token2Type,
                sp.nat(0),
                sp.nat(0),
                sp.self_address
            )

        self.data.lpMapping[params.lpTokenAddress] = params.exchangeAddress

    @sp.entry_point
    def removeExchangePair(self,exchangeAddress):

        sp.set_type(exchangeAddress, sp.TAddress)

        sp.verify( (sp.sender == self.data.adminAddress) |  (sp.sender == self.data.lpDeployer))

        sp.verify(self.data.Registry.contains(exchangeAddress))

        del self.data.Registry[exchangeAddress]

        contractHandle = sp.contract(
            sp.TAddress,
            self.data.routerAddress,
            "DeleteExchange"
        ).open_some()

        sp.transfer(exchangeAddress, sp.mutez(0), contractHandle)

    @sp.entry_point
    def callUpdateExchageAddress(self, lpTokenAddres):

        sp.set_type(lpTokenAddres, sp.TAddress)

        sp.verify(
            self.data.lpMapping.contains(lpTokenAddres)
        )
            
        contractHandle = sp.contract(
            sp.TAddress,
            lpTokenAddres,
            "updateExchangeAddress"
        ).open_some()

        sp.transfer(self.data.lpMapping[lpTokenAddres], sp.mutez(0), contractHandle)

    @sp.entry_point
    def changeLpDeployer(self, newLpDeployer):

        sp.verify(sp.sender == self.data.adminAddress)

        self.data.lpDeployer = newLpDeployer

    @sp.entry_point
    def changeRouterAddress(self, newRouterAddress):

        sp.verify(sp.sender == self.data.adminAddress)

        self.data.routerAddress = newRouterAddress

    @sp.entry_point
    def modifyFee(self, newLpFee):

        sp.verify(sp.sender == self.data.adminAddress)

        self.data.lpFee = newLpFee

    @sp.entry_point
    def changeAdminAddress(self, newAdminAddress):

        sp.verify(sp.sender == self.data.adminAddress)

        self.data.adminAddress = newAdminAddress

    def routerCall(self,exchangeAddress, token1Address, token2Address, token1Id, token2Id, token1Type, token2Type, token1Amount, token2Amount, userAddress):

        contractHandle = sp.contract(
            sp.TRecord(exchangeAddress = sp.TAddress, token1Address = sp.TAddress, token2Address = sp.TAddress, token1Id = sp.TNat, token2Id = sp.TNat, 
            token1Type = sp.TBool, token2Type = sp.TBool, token1Amount = sp.TNat, token2Amount = sp.TNat, userAddress = sp.TAddress, stablePair = sp.TBool),
            self.data.routerAddress,
            "AddExchange"
        ).open_some()

        contractData = sp.record(
            exchangeAddress = exchangeAddress,
            token1Address = token1Address, token1Id = token1Id, token1Type = token1Type,
            token2Address = token2Address, token2Id = token2Id, token2Type = token2Type,
            token1Amount = token1Amount, token2Amount = token2Amount, userAddress = userAddress, stablePair = True
        )

        sp.transfer(contractData, sp.mutez(0), contractHandle)

if "templates" not in __name__:
    @sp.add_test(name = "Plenty Network Stable Pair Deployer")
    def test():

        scenario = sp.test_scenario()
        scenario.h1("PlentySwap Contract")

        scenario.table_of_contents()

        # Deployment Accounts 
        adminAddress = sp.test_account("adminAddress")

        factory = stableFactoryContract(adminAddress.address) 
        scenario += factory

        sp.add_compilation_target(
            "stableDeployer",
            stableFactoryContract(adminAddress.address)
        )