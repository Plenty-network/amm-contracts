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

    # Contract Deployments
    tokenDeployer = TokenFactory.tokenDeployer(adminAddress.address, VolatileContractMetaData, stableContractMetadata, tokenIcon, tokenSymbol, tokenDecimal)
    scenario += tokenDeployer

    volatileDeployer = VolatileFactory.FactoryContract(adminAddress.address)
    scenario += volatileDeployer

    stableDeployer = StableFactory.stableFactoryContract(adminAddress.address)
    scenario += stableDeployer

    swapRouter = Router.Router(adminAddress.address, ctezTokenAddress.address, ctezFlatCurveAddress.address)
    scenario += swapRouter

    # Setting Smart Contracts

    tokenDeployer.modifyStableDeployer(stableDeployer.address).run(sender = adminAddress)

    tokenDeployer.modifyVolatileDeployer(volatileDeployer.address).run(sender = adminAddress)

    volatileDeployer.changeLpDeployer(tokenDeployer.address).run(sender = adminAddress)

    stableDeployer.changeLpDeployer(tokenDeployer.address).run(sender = adminAddress)

    swapRouter.adminOperation(address = volatileDeployer.address, operation = True).run(sender = adminAddress)

    swapRouter.adminOperation(address = stableDeployer.address, operation = True).run(sender = adminAddress)

    volatileDeployer.changeRouterAddress(swapRouter.address).run(sender = adminAddress)

    stableDeployer.changeRouterAddress(swapRouter.address).run(sender = adminAddress)
    
    swapRouter.approveExchangeToken(
        exchangeAddress = ctezFlatCurveAddress.address,
        tokenAddress = ctezTokenAddress.address,
        tokenId = 0,
        amount = 10**36
    ).run(sender = adminAddress)