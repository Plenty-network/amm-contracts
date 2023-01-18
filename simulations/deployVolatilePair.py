import smartpy as sp 

TokenFactory = sp.io.import_script_from_url("file:./tokenDeployer/tokenDeployer.py")

VolatileFactory = sp.io.import_script_from_url("file:./volatileSwapDeployer/volatileDeployer.py")

StableFactory = sp.io.import_script_from_url("file:./stableSwapDeployer/stableDeployer.py")

Router = sp.io.import_script_from_url("file:./Router.py")

@sp.add_test(name = "Plenty Network Factory Contract Setup")
def factoryContractTesting():

    scenario = sp.test_scenario()

    scenario.table_of_contents()

    # Deployment Accounts 
    adminAddress = sp.test_account("adminAddress")

    VolatileContractMetaData = sp.utils.bytes_of_string('ipfs://bafkreignt37tgycplcq6vc4krbdopflxdczt5e447mylyfnai5jmjtfs6i')
    stableContractMetadata = sp.utils.bytes_of_string('ipfs://bafkreiaqibm3yowmk3cww2m6iw72qkqj276hyw4sa2z262sjb2xuihalya')

    tokenIcon = sp.utils.bytes_of_string('https://ipfs.io/ipfs/bafybeifxsyike6qcdkcaautusuyazv47mijpeiktwngjbsgwtehdq74xiy')
    tokenSymbol = sp.utils.bytes_of_string("PNLP") 
    tokenDecimal = sp.utils.bytes_of_string("18")

    ctezTokenAddress = sp.test_account("ctezTokenContract")
    ctezFlatCurveAddress = sp.test_account("ctezFlatCurveContract")

    PLY = sp.test_account("PLY")
    USDC = sp.test_account("USDC")

    PLY_TOKEN_DECIMAL = 10**18
    USDC_TOKEN_DECIMAL = 10**6

    # Contract Deployments
    tokenDeployer = TokenFactory.tokenDeployer(adminAddress.address, VolatileContractMetaData, stableContractMetadata, tokenIcon, tokenSymbol, tokenDecimal)
    scenario += tokenDeployer

    volatileDeployer = VolatileFactory.FactoryContract(adminAddress.address)
    scenario += volatileDeployer


    swapRouter = Router.Router(adminAddress.address, ctezTokenAddress.address, ctezFlatCurveAddress.address)
    scenario += swapRouter

    # Setting Smart Contracts

    tokenDeployer.modifyVolatileDeployer(volatileDeployer.address).run(sender = adminAddress)

    volatileDeployer.changeLpDeployer(tokenDeployer.address).run(sender = adminAddress)

    swapRouter.adminOperation(address = volatileDeployer.address, operation = True).run(sender = adminAddress)

    volatileDeployer.changeRouterAddress(swapRouter.address).run(sender = adminAddress)
    
    swapRouter.approveExchangeToken(
        exchangeAddress = ctezFlatCurveAddress.address,
        tokenAddress = ctezTokenAddress.address,
        tokenId = 0,
        amount = 10**36
    ).run(sender = adminAddress)

    # Deploying Volatile Pair

    tokenDeployer.deployVolatilePair(
        token1Address = PLY.address,
        token1Id = 0,
        token1Type = False,
        token1Amount = 100 * PLY_TOKEN_DECIMAL,
        token2Address = USDC.address,
        token2Id = 0, 
        token2Type = False,
        token2Amount = 100 * USDC_TOKEN_DECIMAL,
        userAddress = adminAddress.address,
        tokenName = sp.utils.bytes_of_string('PLY-USDC PNLP'),
    ).run(sender = adminAddress)