# Plenty Network Factory and Router Contracts

## Folder Structure

- `michelson` : Compiled michelson code.
- `simulations` : Scenarios to explain the working of router and factory contract
- `stableSwapDeployer` : StableSwap AMM contract along with Factory contract for deployment
- `tokenDeployer` : FA1.2 Standard token Contract for LP Positions along with Factory contract for deploying new LP tokens
- `volatileSwapDeployer`: Volatile AMM contract along with Factory contract for deployment

## Contract Files

All contracts are written in [SmartPy](https://smartpy.io). Refer to their elaborate [documentation](https://smartpy.io/docs) for further understanding.

- `stableDeployer` : Factory Contract for deploying stableSwap pairs
- `stableSwap` : AMM which facilitates the trading of assets which have similar underlying value
- `tokenContract` : FA1.2 based token contract which represents liquidity positions for stable as well as volatileSwap
- `tokenDeployer` : Factory contract which deploys LP position and is responsible for deploying stable and volatile trading pairs
- `volatileDeployer` : Factory Contract for deploying volatile pairs
- `volatileSwap` : Uniswap V2 inspired AMM which facilitates the trading of volatile assets
- `Router`: An intermediate contract which helps in trading of tokens across different volatile and stable pairs
