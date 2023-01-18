import smartpy as sp 

token = sp.io.import_script_from_url("file:./tokenDeployer/tokenContract.py")

class tokenDeployer(sp.Contract):

    def __init__(self,_adminAddress, _volatileContractMetadata, _stableContractMetadata, _tokenIcon, _tokenSymbol, _tokenDecimal): 
        
        self.tokenContract = token.FA12()

        self.init(
            adminAddress = _adminAddress,
            volatileAmmDeployer = _adminAddress,
            volatileContractMetadata = _volatileContractMetadata,
            stableAmmDeployer = _adminAddress,
            stableContractMetadata = _stableContractMetadata,
            tokenIcon = _tokenIcon,
            tokenDecimal = _tokenDecimal,
            tokenSymbol = _tokenSymbol,
            volatileRegistry = sp.big_map(tvalue = sp.TMap(sp.TNat, sp.TMap(sp.TAddress, sp.TMap(sp.TNat, sp.TAddress))),tkey = sp.TAddress),
            stableRegistry = sp.big_map(tvalue = sp.TMap(sp.TNat, sp.TMap(sp.TAddress, sp.TMap(sp.TNat, sp.TAddress))), tkey = sp.TAddress),
            paused = False
        )
        
    
    @sp.entry_point
    def deployVolatilePair(self,params):

        sp.set_type(params, sp.TRecord(
            token1Address = sp.TAddress, token1Id = sp.TNat, token1Type = sp.TBool, token1Amount = sp.TNat,
            token2Address = sp.TAddress, token2Id = sp.TNat, token2Type = sp.TBool, token2Amount = sp.TNat,
            tokenName = sp.TBytes, userAddress = sp.TAddress
        ))

        sp.verify(~ self.data.paused)
       
        self.addAddressIfNecessary(params.token1Address)

        self.addAddressIfNecessary(params.token2Address)

        self.addTokenIdIfNecessary(params.token1Address, params.token1Id)

        self.addTokenIdIfNecessary(params.token2Address, params.token2Id)

        self.addSecondTokenIfNecessary(params.token1Address,params.token1Id, params.token2Address)

        self.addSecondTokenIfNecessary(params.token2Address,params.token2Id, params.token1Address)

        sp.verify(~self.data.volatileRegistry[params.token1Address][params.token1Id][params.token2Address].contains(params.token2Id), message = "PairExist")

        lpTokenContract = sp.some(sp.create_contract(
            storage = sp.record(
                ledger = sp.big_map(),
                metadata = sp.big_map(
                    {
                        "": self.data.volatileContractMetadata
                    }
                ),
                token_metadata = sp.big_map(
                    {
                        0 : sp.record(token_id = 0, token_info = sp.map(
                            {
                                "decimals" : self.data.tokenDecimal,
                                "name" : params.tokenName, 
                                "symbol": self.data.tokenSymbol,
                                "icon" : self.data.tokenIcon
                            }
                        ))
                    }
                ),
                totalSupply = sp.nat(0),
                securityCheck = False,
                administrator = self.data.volatileAmmDeployer,
                exchangeAddress = self.data.volatileAmmDeployer
            ),
            contract = self.tokenContract
        ))

        self.data.volatileRegistry[params.token1Address][params.token1Id][params.token2Address][params.token2Id] = lpTokenContract.open_some()

        self.data.volatileRegistry[params.token2Address][params.token2Id][params.token1Address][params.token1Id] = lpTokenContract.open_some()

        # Deploying AMM Contract
        contractHandle = sp.contract(
            sp.TRecord(
                token1Address = sp.TAddress, token1Id = sp.TNat, token1Type = sp.TBool, token1Amount = sp.TNat,
                token2Address = sp.TAddress, token2Id = sp.TNat, token2Type = sp.TBool, token2Amount = sp.TNat,
                lpTokenAddress = sp.TAddress, userAddress = sp.TAddress
            ), 
            self.data.volatileAmmDeployer,
            "deployPair"
        ).open_some()

        contractData = sp.record(
            token1Address = params.token1Address, token1Id = params.token1Id, token1Type = params.token1Type, token1Amount = params.token1Amount,
            token2Address = params.token2Address, token2Id = params.token2Id, token2Type = params.token2Type, token2Amount = params.token2Amount,
            lpTokenAddress = lpTokenContract.open_some(), userAddress = params.userAddress
        )

        sp.transfer(contractData, sp.mutez(0), contractHandle)

    @sp.entry_point
    def deployStablePair(self,params):

        sp.set_type(params, sp.TRecord(
            token1Address = sp.TAddress, token1Id = sp.TNat, token1Type = sp.TBool, token1Amount = sp.TNat,
            token1Precision = sp.TNat, token2Precision = sp.TNat,
            token2Address = sp.TAddress, token2Id = sp.TNat, token2Type = sp.TBool, token2Amount = sp.TNat,
            tokenName = sp.TBytes, userAddress = sp.TAddress
        ))
       
        sp.verify(~self.data.paused)

        self.addStableAddressIfNecessary(params.token1Address)

        self.addStableAddressIfNecessary(params.token2Address)

        self.addStableTokenIdIfNecessary(params.token1Address, params.token1Id)

        self.addStableTokenIdIfNecessary(params.token2Address, params.token2Id)

        self.addStableSecondTokenIfNecessary(params.token1Address,params.token1Id, params.token2Address)

        self.addStableSecondTokenIfNecessary(params.token2Address,params.token2Id, params.token1Address)

        sp.verify(~self.data.stableRegistry[params.token1Address][params.token1Id][params.token2Address].contains(params.token2Id), message = "PairExist")

        lpTokenContract = sp.some(sp.create_contract(
            storage = sp.record(
                ledger = sp.big_map(),
                metadata = sp.big_map(
                    {
                        "": self.data.stableContractMetadata
                    }
                ),
                token_metadata = sp.big_map(
                    {
                        0 : sp.record(token_id = 0, token_info = sp.map(
                            {
                                "decimals" : self.data.tokenDecimal,
                                "name" : params.tokenName, 
                                "symbol": self.data.tokenSymbol,
                                "icon" : self.data.tokenIcon
                            }
                        ))
                    }
                ),
                totalSupply = sp.nat(0),
                securityCheck = False,
                administrator = self.data.stableAmmDeployer,
                exchangeAddress = self.data.stableAmmDeployer
            ),
            contract = self.tokenContract
        ))

        self.data.stableRegistry[params.token1Address][params.token1Id][params.token2Address][params.token2Id] = lpTokenContract.open_some()

        self.data.stableRegistry[params.token2Address][params.token2Id][params.token1Address][params.token1Id] = lpTokenContract.open_some()

        contractHandle = sp.contract(
            sp.TRecord(
                token1Address = sp.TAddress, token1Id = sp.TNat, token1Type = sp.TBool, token1Precision = sp.TNat, token1Amount = sp.TNat,
                token2Address = sp.TAddress, token2Id = sp.TNat, token2Type = sp.TBool, token2Precision = sp.TNat, token2Amount = sp.TNat,
                lpTokenAddress = sp.TAddress, userAddress = sp.TAddress
            ), 
            self.data.stableAmmDeployer,
            "deployPair"
        ).open_some()

        contractData = sp.record(
            token1Address = params.token1Address, token1Id = params.token1Id, token1Type = params.token1Type, token1Precision = params.token1Precision, token1Amount = params.token1Amount,
            token2Address = params.token2Address, token2Id = params.token2Id, token2Type = params.token2Type, token2Precision = params.token2Precision, token2Amount = params.token2Amount,
            lpTokenAddress = lpTokenContract.open_some(), userAddress = params.userAddress
        )

        sp.transfer(contractData, sp.mutez(0), contractHandle)

    @sp.entry_point
    def changeAdminAddress(self,newAdminAddress):

        sp.verify(sp.sender == self.data.adminAddress)

        self.data.adminAddress = newAdminAddress

    @sp.entry_point
    def modifyVolatileDeployer(self, newVolatileDeployer):

        sp.verify(sp.sender == self.data.adminAddress)

        self.data.volatileAmmDeployer = newVolatileDeployer

    @sp.entry_point
    def addPair(self,params):

        sp.set_type(
            params,
            sp.TRecord(
                stableType = sp.TBool, token1Address = sp.TAddress, token2Address = sp.TAddress, 
                token1Id = sp.TNat, token2Id = sp.TNat, token1Type = sp.TBool, token2Type = sp.TBool,
                lpTokenAddress = sp.TAddress, exchangeAddress = sp.TAddress,
                token1Precision = sp.TOption(sp.TNat), token2Precision = sp.TOption(sp.TNat)
            )
        )

        sp.verify(sp.sender == self.data.adminAddress)

        sp.if params.stableType: 

            self.addStableAddressIfNecessary(params.token1Address)

            self.addStableAddressIfNecessary(params.token2Address)

            self.addStableTokenIdIfNecessary(params.token1Address, params.token1Id)

            self.addStableTokenIdIfNecessary(params.token2Address, params.token2Id)

            self.addStableSecondTokenIfNecessary(params.token1Address,params.token1Id, params.token2Address)

            self.addStableSecondTokenIfNecessary(params.token2Address,params.token2Id, params.token1Address)

            sp.verify(~self.data.stableRegistry[params.token1Address][params.token1Id][params.token2Address].contains(params.token2Id), message = "PairExist")

            self.data.stableRegistry[params.token1Address][params.token1Id][params.token2Address][params.token2Id] = params.lpTokenAddress

            self.data.stableRegistry[params.token2Address][params.token2Id][params.token1Address][params.token1Id] = params.lpTokenAddress

            self.addAmmPair(
                params.token1Address, params.token1Id, params.token1Type, params.token1Precision,
                params.token2Address, params.token2Id, params.token2Type, params.token2Precision,
                params.exchangeAddress, params.lpTokenAddress,
                True, self.data.stableAmmDeployer
            )

        sp.else: 

            self.addAddressIfNecessary(params.token1Address)

            self.addAddressIfNecessary(params.token2Address)

            self.addTokenIdIfNecessary(params.token1Address, params.token1Id)

            self.addTokenIdIfNecessary(params.token2Address, params.token2Id)

            self.addSecondTokenIfNecessary(params.token1Address,params.token1Id, params.token2Address)

            self.addSecondTokenIfNecessary(params.token2Address,params.token2Id, params.token1Address)
            
            sp.verify(~self.data.volatileRegistry[params.token1Address][params.token1Id][params.token2Address].contains(params.token2Id), message = "PairExist")

            self.data.volatileRegistry[params.token1Address][params.token1Id][params.token2Address][params.token2Id] = params.lpTokenAddress

            self.data.volatileRegistry[params.token2Address][params.token2Id][params.token1Address][params.token1Id] = params.lpTokenAddress

            self.addAmmPair(
                params.token1Address, params.token1Id, params.token1Type, params.token1Precision,
                params.token2Address, params.token2Id, params.token2Type, params.token2Precision, 
                params.exchangeAddress, params.lpTokenAddress, False , self.data.volatileAmmDeployer
            )

    @sp.entry_point
    def removePair(self,params):

        sp.set_type(
            params,
            sp.TRecord(
                stableType = sp.TBool, token1Address = sp.TAddress, token2Address = sp.TAddress, 
                token1Id = sp.TNat, token2Id = sp.TNat, exchangeAddress = sp.TAddress
            )
        )

        sp.verify(sp.sender == self.data.adminAddress)

        sp.if params.stableType: 

            del self.data.stableRegistry[params.token1Address][params.token1Id][params.token2Address][params.token2Id]

            contractHandle = sp.contract(
                sp.TAddress,
                self.data.stableAmmDeployer,
                "removeExchangePair"
            ).open_some()

            sp.transfer(params.exchangeAddress, sp.mutez(0), contractHandle)

        sp.else: 

            del self.data.volatileRegistry[params.token1Address][params.token1Id][params.token2Address][params.token2Id]

            contractHandle = sp.contract(
                sp.TAddress,
                self.data.volatileAmmDeployer,
                "removeExchangePair"
            ).open_some()

            sp.transfer(params.exchangeAddress, sp.mutez(0), contractHandle)

    @sp.entry_point
    def changeDeployerState(self):

        sp.verify(sp.sender == self.data.adminAddress)

        self.data.paused = ~ self.data.paused

    @sp.entry_point
    def modifyStableDeployer(self, newStableDeployer):

        sp.verify(sp.sender == self.data.adminAddress)

        self.data.stableAmmDeployer = newStableDeployer

    def addStableAddressIfNecessary(self, address): 

        sp.if ~ self.data.stableRegistry.contains(address):
            self.data.stableRegistry[address] = sp.map()
    
    def addStableTokenIdIfNecessary(self,address,id): 

        sp.if ~ self.data.stableRegistry[address].contains(id): 

            self.data.stableRegistry[address][id] = {}

    def addStableSecondTokenIfNecessary(self,address,id,secondAddress): 

        sp.if ~ self.data.stableRegistry[address][id].contains(secondAddress): 

            self.data.stableRegistry[address][id][secondAddress] = {}

    def addAddressIfNecessary(self, address):

        sp.if ~ self.data.volatileRegistry.contains(address):
            self.data.volatileRegistry[address] = sp.map()
    
    def addTokenIdIfNecessary(self,address,id): 

        sp.if ~ self.data.volatileRegistry[address].contains(id): 

            self.data.volatileRegistry[address][id] = {}

    def addSecondTokenIfNecessary(self,address,id,secondAddress): 

        sp.if ~ self.data.volatileRegistry[address][id].contains(secondAddress): 

            self.data.volatileRegistry[address][id][secondAddress] = {}

    def addAmmPair(self,token1Address, token1Id, token1Type, token1Precision, token2Address, token2Id, token2Type, token2Precision, exchangeAddress, lpTokenAddress, stableType, ammDeployer):
    
        sp.if stableType: 

            contractHandle = sp.contract(
                sp.TRecord(
                    token1Address = sp.TAddress, token1Id = sp.TNat, token1Type = sp.TBool, token1Precision = sp.TNat,
                    token2Address = sp.TAddress, token2Id = sp.TNat, token2Type = sp.TBool, token2Precision = sp.TNat,
                    lpTokenAddress = sp.TAddress, exchangeAddress = sp.TAddress,
                    routerCall = sp.TBool
                ),
                ammDeployer,
                "addExistingPair"
            ).open_some()

            contractData = sp.record(
                token1Address = token1Address,
                token1Id = token1Id,
                token1Type = token1Type,
                token1Precision = token1Precision.open_some(),
                token2Address = token2Address,
                token2Id = token2Id, 
                token2Type = token2Type,
                token2Precision = token2Precision.open_some(),
                lpTokenAddress = lpTokenAddress,
                exchangeAddress = exchangeAddress,
                routerCall = True
            )

            sp.transfer(contractData, sp.mutez(0), contractHandle)

        sp.else: 

            contractHandle = sp.contract(
                sp.TRecord(
                    token1Address = sp.TAddress, token1Id = sp.TNat, token1Type = sp.TBool, 
                    token2Address = sp.TAddress, token2Id = sp.TNat, token2Type = sp.TBool,
                    lpTokenAddress = sp.TAddress, exchangeAddress = sp.TAddress,
                    routerCall = sp.TBool
                ),
                ammDeployer,
                "addExistingPair"
            ).open_some()

            contractData = sp.record(
                token1Address = token1Address,
                token1Id = token1Id,
                token1Type = token1Type,
                token2Address = token2Address,
                token2Id = token2Id, 
                token2Type = token2Type,
                lpTokenAddress = lpTokenAddress,
                exchangeAddress = exchangeAddress,
                routerCall = True
            )

            sp.transfer(contractData, sp.mutez(0), contractHandle)


if "templates" not in __name__:
    @sp.add_test(name = "Plenty Network Token Deployer")
    def test():

        scenario = sp.test_scenario()
        scenario.h1("Plenty Network Token Deployment")

        scenario.table_of_contents()

        # Deployment Accounts 
        adminAddress = sp.test_account("adminAddress")

        VolatileContractMetaData = sp.utils.bytes_of_string('ipfs://bafkreignt37tgycplcq6vc4krbdopflxdczt5e447mylyfnai5jmjtfs6i')
        stableContractMetadata = sp.utils.bytes_of_string('ipfs://bafkreiaqibm3yowmk3cww2m6iw72qkqj276hyw4sa2z262sjb2xuihalya')

        tokenIcon = sp.utils.bytes_of_string('https://ipfs.io/ipfs/bafybeifxsyike6qcdkcaautusuyazv47mijpeiktwngjbsgwtehdq74xiy')
        tokenSymbol = sp.utils.bytes_of_string("PNLP") 
        tokenDecimal = sp.utils.bytes_of_string("18")

        tokenFactory = tokenDeployer(adminAddress.address, VolatileContractMetaData, stableContractMetadata, tokenIcon, tokenSymbol, tokenDecimal) 
        scenario += tokenFactory

        sp.add_compilation_target(
            "tokenDeployer",
            tokenDeployer(
                adminAddress.address,
                VolatileContractMetaData,
                stableContractMetadata,
                tokenIcon,
                tokenSymbol,
                tokenDecimal
            )
        )