from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    BasicAuth
)
from aiohttp_socks import ProxyConnector
from web3 import Web3, HTTPProvider
from web3.exceptions import TransactionNotFound
from eth_account import Account
from eth_account.messages import encode_typed_data
from dotenv import load_dotenv
from datetime import datetime
from colorama import *
import asyncio, random, time, pytz, json, sys, re, os

load_dotenv()

wib = pytz.timezone('Asia/Jakarta')

class QuietFinance:
    def __init__(self) -> None:
        self.API_URL = {
            "testnet": "https://testnet-api.quiet.finance",
            "rpc": "https://ethereum-sepolia-rpc.publicnode.com",
            "explorer": "https://sepolia.etherscan.io/tx/",
        }

        self.CONTRACT_ADDRESS = {
            "USDC": "0xf55B2Ab657147E94B228A2575483Ea3C73C88275",
            "qUSD": "0xf58c3e99A217e7c70F238d1914366489Ae6B9F9F",
            "sqUSD": "0x2c41Ed6294A15F5FBC731396fAdb4723ee397f25",
            "faucet": "0x4FE3Ff7d0a60da5ca44923Cd0a8596df54997A82",
            "vault": "0x10c15c29Fb208047df6247514C0416C217e6F6E2",
        }

        self.ERC20_ABI = [
            {
                "type": "function",
                "name": "balanceOf",
                "stateMutability": "view",
                "inputs": [{"name": "account", "type": "address"}],
                "outputs": [{"name": "balance", "type": "uint256"}]
            },
            {
                "type": "function",
                "name": "decimals",
                "stateMutability": "view",
                "inputs": [],
                "outputs": [{"name": "decimals", "type": "uint8"}]
            },
            {
                "type": "function",
                "name": "allowance",
                "stateMutability": "view",
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"}
                ],
                "outputs": [{"name": "remaining", "type": "uint256"}]
            },
            {
                "type": "function",
                "name": "approve",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"name": "success", "type": "bool"}]
            },
            {
                "type": "function",
                "name": "nonces",
                "stateMutability": "view",
                "inputs": [{"name": "owner", "type": "address"}],
                "outputs": [{"name": "nonce", "type": "uint256"}]
            }
        ]

        self.FAUCET_ABI = [
            {
                "type": "function",
                "name": "amount",
                "stateMutability": "view",
                "inputs": [],
                "outputs": [{"name": "amount", "type": "uint256"}]
            },
            {
                "type": "function",
                "name": "claimCooldown",
                "stateMutability": "view",
                "inputs": [],
                "outputs": [{"name": "cooldown", "type": "uint256"}]
            },
            {
                "type": "function",
                "name": "lastClaim",
                "stateMutability": "view",
                "inputs": [{"name": "user", "type": "address"}],
                "outputs": [{"name": "timestamp", "type": "uint256"}]
            },
            {
                "type": "function",
                "name": "bonusAmount",
                "stateMutability": "view",
                "inputs": [],
                "outputs": [{"name": "bonus", "type": "uint256"}]
            },
            {
                "type": "function",
                "name": "bonusClaimed",
                "stateMutability": "view",
                "inputs": [{"name": "user", "type": "address"}],
                "outputs": [{"name": "claimed", "type": "bool"}]
            },
            {
                "type": "function",
                "name": "claim",
                "stateMutability": "nonpayable",
                "inputs": [],
                "outputs": []
            },
            {
                "type": "function",
                "name": "claimBonus",
                "stateMutability": "nonpayable",
                "inputs": [],
                "outputs": []
            }
        ]

        self.PERMIT_ABI = [
            {
                "type": "function",
                "name": "deposit",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "stake", "type": "bool"},
                    {
                        "name": "permit",
                        "type": "tuple",
                        "components": [
                            {"name": "deadline", "type": "uint256"},
                            {"name": "v", "type": "uint8"},
                            {"name": "r", "type": "bytes32"},
                            {"name": "s", "type": "bytes32"}
                        ]
                    }
                ],
                "outputs": []
            },
            {
                "type": "function",
                "name": "withdraw",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "unstake", "type": "bool"},
                    {"name": "instant", "type": "bool"},
                    {
                        "name": "permit",
                        "type": "tuple",
                        "components": [
                            {"name": "deadline", "type": "uint256"},
                            {"name": "v", "type": "uint8"},
                            {"name": "r", "type": "bytes32"},
                            {"name": "s", "type": "bytes32"}
                        ]
                    }
                ],
                "outputs": []
            }
        ]

        self.VAULT_ABI = [
            {
                "type": "function",
                "name": "deposit",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "assets", "type": "uint256"},
                    {"name": "receiver", "type": "address"}
                ],
                "outputs": [{"name": "shares", "type": "uint256"}]
            }
        ]

        self.MINT_AMOUNT = float(os.getenv("USDC_AMOUNT") or "100")
        self.DEPOSIT_AMOUNT = float(os.getenv("qUSD_AMOUNT") or "50")
        self.WITHDRAW_AMOUNT = float(os.getenv("sqUSD_AMOUNT") or "25")

        self.REF_CODE = "4zFiLy" # U can change it with yours.
        self.USE_PROXY = False
        self.ROTATE_PROXY = False
        self.HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        
        self.USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/117.0.0.0"
        ]

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}Quiet Finance {Fore.BLUE + Style.BRIGHT}Auto BOT
            """
            f"""
        {Fore.GREEN + Style.BRIGHT}Rey? {Fore.YELLOW + Style.BRIGHT}<INI WATERMARK>
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    def load_accounts(self):
        filename = "accounts.txt"
        try:
            with open(filename, 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]
            return accounts
        except Exception as e:
            return None
        
    def load_proxies(self):
        filename = "proxy.txt"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                return
            with open(filename, 'r') as f:
                self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"
    
    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
    
    def build_proxy_config(self, proxy=None):
        if not proxy:
            return None, None, None

        if proxy.startswith("socks"):
            connector = ProxyConnector.from_url(proxy)
            return connector, None, None

        elif proxy.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy)
            if match:
                username, password, host_port = match.groups()
                clean_url = f"http://{host_port}"
                auth = BasicAuth(username, password)
                return None, clean_url, auth
            else:
                return None, proxy, None
    
    def display_proxy(self, proxy_url=None):
        if not proxy_url: return "No Proxy"

        proxy_url = re.sub(r"^(http|https|socks4|socks5)://", "", proxy_url)

        if "@" in proxy_url:
            proxy_url = proxy_url.split("@", 1)[1]

        return proxy_url
    
    def initialize_headers(self, address: str):
        if address not in self.HEADERS:
            self.HEADERS[address] = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
                "Origin": "https://testnet.quiet.finance",
                "Pragma": "no-cache",
                "Ref-Code": self.REF_CODE,
                "Referer": "https://testnet.quiet.finance/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "User-Agent": random.choice(self.USER_AGENTS)
            }

        return self.HEADERS[address].copy()
    
    def generate_address(self, private_key: str):
        try:
            acc = Account.from_key(private_key)
            address = acc.address
            return address
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Generate Address Failed {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None
        
    def mask_account(self, account):
        try:
            mask_account = account[:6] + '*' * 6 + account[-6:]
            return mask_account
        except Exception as e:
            return None
        
    async def get_web3_with_check(self, address: str, retries=3, timeout=60):
        request_kwargs = {"timeout": timeout}

        if self.USE_PROXY:
            proxy_url = self.get_next_proxy_for_account(address)
            request_kwargs["proxies"] = {
                "http": proxy_url,
                "https": proxy_url,
            }

        for attempt in range(retries):
            try:
                provider = HTTPProvider(
                    self.API_URL['rpc'],
                    request_kwargs=request_kwargs
                )
                web3 = Web3(provider)

                await asyncio.to_thread(lambda: web3.eth.block_number)
                return web3
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(3)
                    continue
                raise Exception(f"Failed to Connect to RPC: {str(e)}")

    async def get_token_balance(self, address: str, asset_address=None):
        try:
            web3 = await self.get_web3_with_check(address)

            if asset_address is None:
                raw_balance = await asyncio.to_thread(
                    web3.eth.get_balance,
                    address
                )

                token_balance = raw_balance / (10**18)
            else:
                asset = web3.to_checksum_address(asset_address)

                contract = web3.eth.contract(
                    address=asset,
                    abi=self.ERC20_ABI
                )

                raw_balance, decimals = await asyncio.gather(
                    asyncio.to_thread(
                        contract.functions.balanceOf(address).call
                    ),
                    asyncio.to_thread(
                        contract.functions.decimals().call
                    )
                )

                token_balance = raw_balance / (10**decimals)

            return token_balance
        except Exception as e:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None

    async def get_daily_faucet(self, address: str):
        try:
            web3 = await self.get_web3_with_check(address)
            router = web3.to_checksum_address(self.CONTRACT_ADDRESS["faucet"])

            contract = web3.eth.contract(
                address=router,
                abi=self.FAUCET_ABI
            )

            raw_amount, last_claim = await asyncio.gather(
                asyncio.to_thread(
                    contract.functions.amount().call
                ),
                asyncio.to_thread(
                    contract.functions.lastClaim(address).call
                )
            )

            amount = raw_amount / (10**6)

            return {
                "amount": amount,
                "lastClaim": last_claim
            }
        except Exception as e:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None

    async def get_bonus_faucet(self, address: str):
        try:
            web3 = await self.get_web3_with_check(address)
            router = web3.to_checksum_address(self.CONTRACT_ADDRESS["faucet"])

            contract = web3.eth.contract(
                address=router,
                abi=self.FAUCET_ABI
            )

            raw_amount, bonus_claimed = await asyncio.gather(
                asyncio.to_thread(
                    contract.functions.bonusAmount().call
                ),
                asyncio.to_thread(
                    contract.functions.bonusClaimed(address).call
                )
            )

            amount = raw_amount / (10**6)

            return {
                "bonusAmount": amount,
                "bonusClaimed": bonus_claimed
            }
        except Exception as e:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None
        
    async def send_raw_transaction_with_retries(self, private_key, web3, tx, retries=5):
        for attempt in range(retries):
            try:
                signed_tx = web3.eth.account.sign_transaction(tx, private_key)

                raw_tx = await asyncio.to_thread(
                    web3.eth.send_raw_transaction,
                    signed_tx.raw_transaction
                )

                return web3.to_hex(raw_tx)
            except TransactionNotFound:
                pass
            except Exception as e:
                self.log(
                    f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} [Attempt {attempt + 1}] Send TX Error: {str(e)} {Style.RESET_ALL}"
                )
            await asyncio.sleep(2 ** attempt)
        raise Exception("Transaction Hash Not Found After Maximum Retries")

    async def wait_for_receipt_with_retries(self, web3, tx_hash, retries=5):
        for attempt in range(retries):
            try:
                receipt = await asyncio.to_thread(
                    web3.eth.wait_for_transaction_receipt,
                    tx_hash,
                    60
                )
                return receipt
            except TransactionNotFound:
                pass
            except Exception as e:
                self.log(
                    f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} [Attempt {attempt + 1}] Wait for Receipt Error: {str(e)} {Style.RESET_ALL}"
                )
            await asyncio.sleep(2 ** attempt)
        raise Exception("Transaction Receipt Not Found After Maximum Retries")
    
    async def claim_faucet(self, private_key: str, address: str, faucet_type: str):
        try:
            web3 = await self.get_web3_with_check(address)

            router = web3.to_checksum_address(self.CONTRACT_ADDRESS['faucet'])
            contract = web3.eth.contract(address=router, abi=self.FAUCET_ABI)

            if faucet_type == "Daily":
                claim_func = contract.functions.claim()
            elif faucet_type == "Bonus":
                claim_func = contract.functions.claimBonus()

            estimated_gas = await asyncio.to_thread(
                claim_func.estimate_gas,
                {
                    "from": address
                }
            )

            latest_block = await asyncio.to_thread(web3.eth.get_block, "latest")
            base_fee = latest_block["baseFeePerGas"]

            max_priority_fee = web3.to_wei(1.5, "gwei")
            max_fee = base_fee + max_priority_fee

            nonce = await asyncio.to_thread(
                web3.eth.get_transaction_count,
                address,
                "pending"
            )

            chain_id = await asyncio.to_thread(lambda: web3.eth.chain_id)

            claim_tx = await asyncio.to_thread(
                claim_func.build_transaction,
                {
                    "from": address,
                    "gas": int(estimated_gas * 1.2),
                    "maxFeePerGas": int(max_fee),
                    "maxPriorityFeePerGas": int(max_priority_fee),
                    "nonce": nonce,
                    "chainId": chain_id,
                }
            )

            tx_hash = await self.send_raw_transaction_with_retries(private_key, web3, claim_tx)
            receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)

            return {
                "tx_hash": tx_hash, 
                "block_number": receipt.blockNumber
            }
        except Exception as e:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None
        
    def build_permit_data(self, private_key: str, address: str, asset: str, spender: str, nonce: str, amount_in: int):
        try:
            deadline = int(time.time()) + 3600

            typed_data = {
                "domain": {
                    "name": "USDC",
                    "version": "1",
                    "chainId": 11155111,
                    "verifyingContract": asset,
                },
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                        {"name": "verifyingContract", "type": "address"},
                    ],
                    "Permit": [
                        {"name": "owner", "type": "address"},
                        {"name": "spender", "type": "address"},
                        {"name": "value", "type": "uint256"},
                        {"name": "nonce", "type": "uint256"},
                        {"name": "deadline", "type": "uint256"},
                    ],
                },
                "primaryType": "Permit",
                "message": {
                    "owner": address,
                    "spender": spender,
                    "value": amount_in,
                    "nonce": nonce,
                    "deadline": deadline,
                },
            }

            signable = encode_typed_data(full_message=typed_data)
            signed = Account.sign_message(signable, private_key)

            r_bytes = signed.r.to_bytes(32, "big")
            s_bytes = signed.s.to_bytes(32, "big")

            return (
                deadline,
                signed.v,
                r_bytes,
                s_bytes,
            )

        except Exception as e:
            raise Exception(f"Failed to build permit data: {e}")
        
    async def mint(self, private_key: str, address: str, amount: float):
        try:
            web3 = await self.get_web3_with_check(address)

            token = web3.to_checksum_address(self.CONTRACT_ADDRESS["USDC"])
            router = web3.to_checksum_address(self.CONTRACT_ADDRESS["vault"])

            token_contract = web3.eth.contract(
                address=token,
                abi=self.ERC20_ABI
            )

            decimals, nonce = await asyncio.gather(
                asyncio.to_thread(
                    token_contract.functions.decimals().call
                ),
                asyncio.to_thread(
                    token_contract.functions.nonces(address).call
                )
            )

            amount_in = int(amount * (10**decimals))

            permit = self.build_permit_data(private_key, address, token, router, nonce, amount_in)

            router_contract = web3.eth.contract(address=router, abi=self.PERMIT_ABI)
            
            mint_func = router_contract.functions.deposit(amount_in, False, permit)

            estimated_gas = await asyncio.to_thread(
                mint_func.estimate_gas,
                {
                    "from": address
                }
            )

            latest_block = await asyncio.to_thread(web3.eth.get_block, "latest")
            base_fee = latest_block["baseFeePerGas"]

            max_priority_fee = web3.to_wei(1.5, "gwei")
            max_fee = base_fee + max_priority_fee

            nonce = await asyncio.to_thread(
                web3.eth.get_transaction_count,
                address,
                "pending"
            )

            chain_id = await asyncio.to_thread(lambda: web3.eth.chain_id)

            mint_tx = await asyncio.to_thread(
                mint_func.build_transaction,
                {
                    "from": address,
                    "gas": int(estimated_gas * 1.2),
                    "maxFeePerGas": int(max_fee),
                    "maxPriorityFeePerGas": int(max_priority_fee),
                    "nonce": nonce,
                    "chainId": chain_id,
                }
            )

            tx_hash = await self.send_raw_transaction_with_retries(private_key, web3, mint_tx)
            receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)

            return {
                "tx_hash": tx_hash, 
                "block_number": receipt.blockNumber
            }
        except Exception as e:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None
        
    async def approving_token(self, private_key: str, address: str, asset: str, spender: str, amount_to_wei: int):
        try:
            web3 = await self.get_web3_with_check(address)
            
            token_contract = web3.eth.contract(address=asset, abi=self.ERC20_ABI)
            allowance = await asyncio.to_thread(
                token_contract.functions.allowance(address, spender).call
            )

            if allowance < amount_to_wei:
                approve_func = token_contract.functions.approve(spender, 2**256 - 1)

                estimated_gas = await asyncio.to_thread(
                    approve_func.estimate_gas,
                    {
                        "from": address
                    }
                )

                latest_block = await asyncio.to_thread(web3.eth.get_block, "latest")
                base_fee = latest_block["baseFeePerGas"]

                max_priority_fee = web3.to_wei(1.5, "gwei")
                max_fee = base_fee + max_priority_fee

                nonce = await asyncio.to_thread(
                    web3.eth.get_transaction_count,
                    address,
                    "pending"
                )

                chain_id = await asyncio.to_thread(lambda: web3.eth.chain_id)

                approve_tx = await asyncio.to_thread(
                    approve_func.build_transaction,
                    {
                        "from": address,
                        "gas": int(estimated_gas * 1.2),
                        "maxFeePerGas": int(max_fee),
                        "maxPriorityFeePerGas": int(max_priority_fee),
                        "nonce": nonce,
                        "chainId": chain_id,
                    }
                )
                tx_hash = await self.send_raw_transaction_with_retries(private_key, web3, approve_tx)
                receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)

                block_number = receipt.blockNumber
                explorer = self.API_URL["explorer"]

                self.log(
                    f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} Token Approved {Style.RESET_ALL}                                   "
                )
                self.log(
                    f"{Fore.BLUE+Style.BRIGHT}   Block   :{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
                )
                self.log(
                    f"{Fore.BLUE+Style.BRIGHT}   Tx Hash :{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
                )
                self.log(
                    f"{Fore.BLUE+Style.BRIGHT}   Explorer:{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {explorer}{tx_hash} {Style.RESET_ALL}"
                )
                
                await asyncio.sleep(random.uniform(3.0, 5.0))

            return True
        except Exception as e:
            raise Exception(f"Approving Token Contract Failed: {str(e)}")
        
    async def deposit(self, private_key: str, address: str, amount: float):
        try:
            web3 = await self.get_web3_with_check(address)

            token = web3.to_checksum_address(self.CONTRACT_ADDRESS['qUSD'])
            router = web3.to_checksum_address(self.CONTRACT_ADDRESS['sqUSD'])

            token_contract = web3.eth.contract(
                address=token,
                abi=self.ERC20_ABI
            )

            decimals = await asyncio.to_thread(
                token_contract.functions.decimals().call
            )

            amount_in = int(amount * (10**decimals))

            await self.approving_token(private_key, address, token, router, amount_in)

            router_contract = web3.eth.contract(address=router, abi=self.VAULT_ABI)
            
            deposit_func = router_contract.functions.deposit(amount_in, address)

            estimated_gas = await asyncio.to_thread(
                deposit_func.estimate_gas,
                {
                    "from": address
                }
            )

            latest_block = await asyncio.to_thread(web3.eth.get_block, "latest")
            base_fee = latest_block["baseFeePerGas"]

            max_priority_fee = web3.to_wei(1.5, "gwei")
            max_fee = base_fee + max_priority_fee

            nonce = await asyncio.to_thread(
                web3.eth.get_transaction_count,
                address,
                "pending"
            )

            chain_id = await asyncio.to_thread(lambda: web3.eth.chain_id)

            deposit_tx = await asyncio.to_thread(
                deposit_func.build_transaction,
                {
                    "from": address,
                    "gas": int(estimated_gas * 1.2),
                    "maxFeePerGas": int(max_fee),
                    "maxPriorityFeePerGas": int(max_priority_fee),
                    "nonce": nonce,
                    "chainId": chain_id,
                }
            )

            tx_hash = await self.send_raw_transaction_with_retries(private_key, web3, deposit_tx)
            receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)

            return {
                "tx_hash": tx_hash, 
                "block_number": receipt.blockNumber
            }
        except Exception as e:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None
        
    async def withdraw(self, private_key: str, address: str, amount: float):
        try:
            web3 = await self.get_web3_with_check(address)

            token = web3.to_checksum_address(self.CONTRACT_ADDRESS['sqUSD'])
            router = web3.to_checksum_address(self.CONTRACT_ADDRESS['vault'])

            token_contract = web3.eth.contract(
                address=token,
                abi=self.ERC20_ABI
            )

            decimals = await asyncio.to_thread(
                token_contract.functions.decimals().call
            )

            amount_in = int(amount * (10**decimals))

            await self.approving_token(private_key, address, token, router, amount_in)

            permit = (
                0,
                0,
                b"\x00"*32,
                b"\x00"*32
            )

            router_contract = web3.eth.contract(address=router, abi=self.PERMIT_ABI)
            
            withdraw_func = router_contract.functions.withdraw(amount_in, True, True, permit)

            estimated_gas = await asyncio.to_thread(
                withdraw_func.estimate_gas,
                {
                    "from": address
                }
            )

            latest_block = await asyncio.to_thread(web3.eth.get_block, "latest")
            base_fee = latest_block["baseFeePerGas"]

            max_priority_fee = web3.to_wei(1.5, "gwei")
            max_fee = base_fee + max_priority_fee

            nonce = await asyncio.to_thread(
                web3.eth.get_transaction_count,
                address,
                "pending"
            )

            chain_id = await asyncio.to_thread(lambda: web3.eth.chain_id)

            withdraw_tx = await asyncio.to_thread(
                withdraw_func.build_transaction,
                {
                    "from": address,
                    "gas": int(estimated_gas * 1.2),
                    "maxFeePerGas": int(max_fee),
                    "maxPriorityFeePerGas": int(max_priority_fee),
                    "nonce": nonce,
                    "chainId": chain_id,
                }
            )

            tx_hash = await self.send_raw_transaction_with_retries(private_key, web3, withdraw_tx)
            receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)

            return {
                "tx_hash": tx_hash, 
                "block_number": receipt.blockNumber
            }
        except Exception as e:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None
        
    def print_question(self):
        while True:
            try:
                print(f"{Fore.WHITE + Style.BRIGHT}1. Run With Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. Run Without Proxy{Style.RESET_ALL}")
                proxy_choice = int(input(f"{Fore.BLUE + Style.BRIGHT}Choose [1/2] -> {Style.RESET_ALL}").strip())

                if proxy_choice in [1, 2]:
                    proxy_type = (
                        "With" if proxy_choice == 1 else 
                        "Without"
                    )
                    print(f"{Fore.GREEN + Style.BRIGHT}Run {proxy_type} Proxy Selected.{Style.RESET_ALL}")
                    self.USE_PROXY = True if proxy_choice == 1 else False
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Please enter either 1 or 2.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1 or 2).{Style.RESET_ALL}")

        if self.USE_PROXY:
            while True:
                rotate_proxy = input(f"{Fore.BLUE + Style.BRIGHT}Rotate Invalid Proxy? [y/n] -> {Style.RESET_ALL}").strip()
                if rotate_proxy in ["y", "n"]:
                    self.ROTATE_PROXY = True if rotate_proxy == "y" else False
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter 'y' or 'n'.{Style.RESET_ALL}")

    async def ensure_ok(self, response):
        if response.status >= 400:
            error_text = await response.text()
            raise Exception(f"HTTP {response.status}: {error_text}")
    
    async def check_connection(self, proxy_url=None):
        url = "https://api.ipify.org?format=json"

        connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(url=url, proxy=proxy, proxy_auth=proxy_auth) as response:
                    await self.ensure_ok(response)
                    return True
        except (Exception, ClientResponseError) as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status  :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Connection Not 200 OK {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
        
        return None
    
    async def points_stats(self, address: str, proxy_url=None, retries=5):
        url = f"{self.API_URL['testnet']}/points/{address}"
        
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                headers = self.initialize_headers(address)

                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        await self.ensure_ok(response)
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Stats   :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed to Fetch Stats {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
    
    async def points_tasks(self, address: str, proxy_url=None, retries=5):
        url = f"{self.API_URL['testnet']}/points/tasks/{address}"
        
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                headers = self.initialize_headers(address)

                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        await self.ensure_ok(response)
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Tasks   :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed to Fetch Tasks {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
    
    async def claim_tasks(self, address: str, task_id: str, proxy_url=None, retries=5):
        url = f"{self.API_URL['testnet']}/points/tasks/claim/{address}"
        
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                headers = self.initialize_headers(address)
                params = {
                    "task_id": task_id
                }

                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, params=params, proxy=proxy, proxy_auth=proxy_auth) as response:
                        result = await response.text()

                        if response.status == 400:
                            err_msg = json.loads(result).get("detail", "Failed to Claim")
                            self.log(
                                f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
                                f"{Fore.WHITE+Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                                f"{Fore.YELLOW+Style.BRIGHT} {err_msg} {Style.RESET_ALL}"
                            )
                            return None
                        
                        await self.ensure_ok(response)
                        return result
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed to Claim {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
    
    async def process_check_connection(self, address: str, proxy_url=None):
        while True:
            if self.USE_PROXY:
                proxy_url = self.get_next_proxy_for_account(address)

            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Proxy   :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {self.display_proxy(proxy_url)} {Style.RESET_ALL}"
            )

            is_valid = await self.check_connection(proxy_url)
            if is_valid: return True

            if self.ROTATE_PROXY:
                proxy_url = self.rotate_proxy_for_account(address)
                await asyncio.sleep(1)
                continue

            return False
        
    async def process_points_stats(self, address: str, proxy_url=None):
        stats = await self.points_stats(address, proxy_url)
        if not stats: return False

        self.log(f"{Fore.CYAN+Style.BRIGHT}Stats   :{Style.RESET_ALL}")

        activity_points = stats.get("activity_points", 0)
        referral_points = stats.get("referral_points", 0)
        user_rank = stats.get("rank", "N/A")

        total_points = activity_points + referral_points

        self.log(
            f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
            f"{Fore.GREEN+Style.BRIGHT}Points:{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {total_points} {Style.RESET_ALL}"
        )
        self.log(
            f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
            f"{Fore.GREEN+Style.BRIGHT}Rank  :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} #{user_rank} {Style.RESET_ALL}"
        )

    async def process_claim_faucet(self, private_key: str, address: str):
        self.log(f"{Fore.CYAN+Style.BRIGHT}Faucet  :{Style.RESET_ALL}")

        for faucet_type in ["Daily", "Bonus"]:
            self.log(
                f"{Fore.GREEN+Style.BRIGHT} ● {Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT}{faucet_type}{Style.RESET_ALL}"
            )

            if faucet_type == "Daily":
                faucet = await self.get_daily_faucet(address)

                if not faucet:
                    self.log(
                        f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                        f"{Fore.YELLOW+Style.BRIGHT} Failed to Fetch Status {Style.RESET_ALL}"
                    )
                    continue

                amount = faucet["amount"]
                last_claim = faucet["lastClaim"]
                next_claim = last_claim + 86400
                timestamp = int(time.time())
                
                if timestamp < next_claim:
                    next_claim_dt = datetime.fromtimestamp(next_claim).astimezone(wib).strftime('%x %X %Z')

                    self.log(
                        f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                        f"{Fore.YELLOW+Style.BRIGHT} Not Time to Claim {Style.RESET_ALL}"
                    )
                    self.log(
                        f"{Fore.BLUE+Style.BRIGHT}   Next At :{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {next_claim_dt} {Style.RESET_ALL}"
                    )
                    continue

            elif faucet_type == "Bonus":
                faucet = await self.get_bonus_faucet(address)

                if not faucet:
                    self.log(
                        f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                        f"{Fore.YELLOW+Style.BRIGHT} Failed to Fetch Status {Style.RESET_ALL}"
                    )
                    continue

                amount = faucet["bonusAmount"]
                bonus_claimed = faucet["bonusClaimed"]

                if bonus_claimed:
                    self.log(
                        f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                        f"{Fore.YELLOW+Style.BRIGHT} Already Claimed {Style.RESET_ALL}"
                    )
                    continue

            claim = await self.claim_faucet(private_key, address, faucet_type)
            if not claim:
                self.log(
                    f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Perform On-Chain Failed {Style.RESET_ALL}"
                )
                continue

            block_number = claim["block_number"]
            tx_hash = claim["tx_hash"]
            explorer = self.API_URL["explorer"]

            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}                                   "
            )
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Amount  :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {amount} USDC {Style.RESET_ALL}                                   "
            )
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Block   :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Tx Hash :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Explorer:{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {explorer}{tx_hash} {Style.RESET_ALL}"
            )

            await asyncio.sleep(random.uniform(3.0, 5.0))

    async def process_mint(self, private_key: str, address: str, amount: float):
        self.log(
            f"{Fore.CYAN+Style.BRIGHT}Mint    :{Style.RESET_ALL}"
            f"{Fore.BLUE+Style.BRIGHT} USDC to qUSD {Style.RESET_ALL}"
        )

        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Amount  :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {amount} USDC {Style.RESET_ALL}                                   "
        )

        balance = await self.get_token_balance(address, self.CONTRACT_ADDRESS["USDC"])
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Balance :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {balance} USDC {Style.RESET_ALL}                                   "
        )

        if balance is None:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Failed to Fetch USDC Token Balance {Style.RESET_ALL}"
            )
            return False
        
        if balance < amount:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Insufficient USDC Token Balance {Style.RESET_ALL}"
            )
            return False

        mint = await self.mint(private_key, address, amount)
        if not mint:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Perform On-Chain Failed {Style.RESET_ALL}"
            )
            return False

        block_number = mint["block_number"]
        tx_hash = mint["tx_hash"]
        explorer = self.API_URL["explorer"]

        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
            f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}                                   "
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Block   :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Tx Hash :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Explorer:{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {explorer}{tx_hash} {Style.RESET_ALL}"
        )

        await asyncio.sleep(random.uniform(3.0, 5.0))

    async def process_deposit(self, private_key: str, address: str, amount: float):
        self.log(
            f"{Fore.CYAN+Style.BRIGHT}Deposit :{Style.RESET_ALL}"
            f"{Fore.BLUE+Style.BRIGHT} qUSD to sqUSD {Style.RESET_ALL}"
        )

        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Amount  :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {amount} qUSD {Style.RESET_ALL}                                   "
        )

        balance = await self.get_token_balance(address, self.CONTRACT_ADDRESS["qUSD"])
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Balance :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {balance} qUSD {Style.RESET_ALL}                                   "
        )

        if balance is None:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Failed to Fetch qUSD Token Balance {Style.RESET_ALL}"
            )
            return False
        
        if balance < amount:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Insufficient qUSD Token Balance {Style.RESET_ALL}"
            )
            return False

        deposit = await self.deposit(private_key, address, amount)
        if not deposit:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Perform On-Chain Failed {Style.RESET_ALL}"
            )
            return False

        block_number = deposit["block_number"]
        tx_hash = deposit["tx_hash"]
        explorer = self.API_URL["explorer"]

        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
            f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}                                   "
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Block   :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Tx Hash :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Explorer:{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {explorer}{tx_hash} {Style.RESET_ALL}"
        )

        await asyncio.sleep(random.uniform(3.0, 5.0))

    async def process_withdraw(self, private_key: str, address: str, amount: float):
        self.log(
            f"{Fore.CYAN+Style.BRIGHT}Withdraw:{Style.RESET_ALL}"
            f"{Fore.BLUE+Style.BRIGHT} sqUSD to USDC {Style.RESET_ALL}"
        )

        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Amount  :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {amount} sqUSD {Style.RESET_ALL}                                   "
        )

        balance = await self.get_token_balance(address, self.CONTRACT_ADDRESS["sqUSD"])
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Balance :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {balance} sqUSD {Style.RESET_ALL}                                   "
        )

        if balance is None:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Failed to Fetch sqUSD Token Balance {Style.RESET_ALL}"
            )
            return False
        
        if balance < amount:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Insufficient sqUSD Token Balance {Style.RESET_ALL}"
            )
            return False

        withdraw = await self.withdraw(private_key, address, amount)
        if not withdraw:
            self.log(
                f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Perform On-Chain Failed {Style.RESET_ALL}"
            )
            return False

        block_number = withdraw["block_number"]
        tx_hash = withdraw["tx_hash"]
        explorer = self.API_URL["explorer"]

        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Status  :{Style.RESET_ALL}"
            f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}                                   "
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Block   :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Tx Hash :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
        )
        self.log(
            f"{Fore.BLUE+Style.BRIGHT}   Explorer:{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {explorer}{tx_hash} {Style.RESET_ALL}"
        )

        await asyncio.sleep(random.uniform(3.0, 5.0))
        
    async def process_points_tasks(self, address: str, proxy_url=None):
        tasks = await self.points_tasks(address, proxy_url)
        if not tasks: return False

        self.log(f"{Fore.CYAN+Style.BRIGHT}Tasks   :{Style.RESET_ALL}")

        for task in tasks:
            task_id = task["id"]
            status = task["status"]
            reward = task["reward"]

            if status == "CLAIMED":
                self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} Already Claimed {Style.RESET_ALL}"
                )
                continue

            claim = await self.claim_tasks(address, task_id, proxy_url)
            if not claim: continue

            claim_msg = claim.strip('"')

            if claim_msg == "ok":
                self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} Claimed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT} Reward: {Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT}{reward} Points{Style.RESET_ALL}"
                )
            else:
                self.log(
                    f"{Fore.MAGENTA+Style.BRIGHT} ● {Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {claim_msg} {Style.RESET_ALL}"
                )

    async def process_accounts(self, private_key: str, address: str, proxy_url=None):
        is_valid = await self.process_check_connection(address, proxy_url)
        if not is_valid: return False

        if self.USE_PROXY:
            proxy_url = self.get_next_proxy_for_account(address)

        await self.process_points_stats(address, proxy_url)
        await self.process_claim_faucet(private_key, address)
        await self.process_mint(private_key, address, self.MINT_AMOUNT)
        await self.process_deposit(private_key, address, self.DEPOSIT_AMOUNT)
        await self.process_withdraw(private_key, address, self.WITHDRAW_AMOUNT)
        await self.process_points_tasks(address, proxy_url)
        
    async def main(self):
        try:
            accounts = self.load_accounts()
            if not accounts:
                print(f"{Fore.RED+Style.BRIGHT}No Accounts Loaded.{Style.RESET_ALL}")
                return False
            
            self.print_question()

            while True:
                self.clear_terminal()
                self.welcome()
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT}Account's Total: {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{len(accounts)}{Style.RESET_ALL}"
                )
                
                if self.USE_PROXY: self.load_proxies()

                separator = "=" * 25
                for idx, private_key in enumerate(accounts, start=1):
                    self.log(
                        f"{Fore.CYAN + Style.BRIGHT}{separator}[{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} {idx} {Style.RESET_ALL}"
                        f"{Fore.CYAN + Style.BRIGHT}-{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} {len(accounts)} {Style.RESET_ALL}"
                        f"{Fore.CYAN + Style.BRIGHT}]{separator}{Style.RESET_ALL}"
                    )

                    address = self.generate_address(private_key)
                    if not address: continue

                    self.log(
                        f"{Fore.CYAN+Style.BRIGHT}Address :{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {self.mask_account(address)} {Style.RESET_ALL}"
                    )
                    
                    await self.process_accounts(private_key, address)
                    await asyncio.sleep(random.uniform(2.0, 3.0))

                self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}"*72)

                delay = 24 * 60 * 60
                while delay > 0:
                    formatted_time = self.format_seconds(delay)
                    print(
                        f"{Fore.CYAN+Style.BRIGHT}[ Wait for{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.BLUE+Style.BRIGHT}All Accounts Have Been Processed...{Style.RESET_ALL}",
                        end="\r",
                        flush=True
                    )
                    await asyncio.sleep(1)
                    delay -= 1

        except Exception as e:
            raise e
        except asyncio.CancelledError:
            raise

if __name__ == "__main__":
    bot = QuietFinance()
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Quiet Finance - BOT{Style.RESET_ALL}                                       "                              
        )
    finally:
        sys.exit(0)