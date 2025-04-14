import json
import os
import random
import sys
import time
from web3 import Web3, HTTPProvider
import requests
from colorama import init, Fore, Style
from alive_progress import alive_bar
import threading
from eth_account import Account
from dotenv import load_dotenv

# Initialize colorama for colored output
init()

# Network configuration
network = {
    'name': 'Tea Sepolia Testnet 🌐',
    'rpc': 'https://tea-sepolia.g.alchemy.com/public',
    'chainId': 10218,
    'symbol': 'TEA',
    'explorer': 'https://sepolia.tea.xyz/'
}

# Contract ABIs
erc20_abi = [
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
]

sttea_abi = [
    {"constant": False, "inputs": [], "name": "stake", "outputs": [], "payable": True, "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "type": "function"}
]

sttea_contract_address = '0x04290DACdb061C6C9A0B9735556744be49A64012'

# Load configuration
def load_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        validate_config(config)
        return config
    except Exception as e:
        print(f"{Fore.RED}Error loading config.json: {e} ❌{Style.RESET_ALL}")
        sys.exit(1)

def validate_config(config):
    if 'maxConcurrentThreads' not in config or not isinstance(config['maxConcurrentThreads'], int) or config['maxConcurrentThreads'] < 1:
        print(f"{Fore.RED}Invalid maxConcurrentThreads in config.json. Must be a positive number.{Style.RESET_ALL}")
        sys.exit(1)

def load_proxies():
    try:
        with open('proxies.txt', 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        if not proxies:
            print(f"{Fore.YELLOW}No proxies found in proxies.txt. Running without proxy.{Style.RESET_ALL}")
            return []
        return proxies
    except Exception as e:
        print(f"{Fore.RED}Error reading proxies.txt: {e} ❌{Style.RESET_ALL}")
        return []

def load_wallets():
    try:
        with open('private_keys.txt', 'r') as f:
            private_keys = [line.strip() for line in f if line.strip()]
        if not private_keys:
            print(f"{Fore.RED}No private keys found in private_keys.txt. 🚫{Style.RESET_ALL}")
            sys.exit(1)
        return private_keys
    except Exception as e:
        print(f"{Fore.RED}Error reading private_keys.txt: {e} ❌{Style.RESET_ALL}")
        sys.exit(1)

def shuffle_array(array):
    array = array.copy()
    for i in range(len(array) - 1, 0, -1):
        j = random.randint(0, i)
        array[i], array[j] = array[j], array[i]
    return array

def parse_proxy(proxy):
    if not proxy:
        return None
    # Accept proxy as-is if it starts with http:// or https://
    if proxy.startswith('http://') or proxy.startswith('https://'):
        return proxy
    # Default to http:// for bare proxies (username:password@host:port or host:port)
    return f'http://{proxy}'

def show_spinner(message, duration=0):
    if duration:
        with alive_bar(duration, title=message, bar=None, spinner='dots') as bar:
            time.sleep(duration)
    else:
        print(f"{Fore.YELLOW}{message} ⠹{Style.RESET_ALL}", end='', flush=True)

def confirm_transaction(details):
    print(f"{Fore.WHITE}┌─── Transaction Preview ───┐{Style.RESET_ALL}")
    for key, value in details.items():
        print(f"{Fore.WHITE}│ {key:<10} : {Fore.CYAN}{value}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}└──────────────────────────┘{Style.RESET_ALL}")
    answer = input(f"{Fore.YELLOW}Confirm transaction? (y/n): {Style.RESET_ALL}").lower()
    return answer in ['y', 'yes']

def display_banner(w3):
    try:
        block_number = w3.eth.block_number
        gas_price = w3.eth.gas_price
        gas_price_gwei = w3.from_wei(gas_price, 'gwei')
        banner_text = f"""
{Fore.WHITE}==============================================={Style.RESET_ALL}
{Fore.CYAN}                TEA SEPOLIA AUTO BOT{Style.RESET_ALL}
{Fore.YELLOW}     Join Us: https://t.me/AirdropInsiderID {Style.RESET_ALL}
{Fore.YELLOW}        Block: {block_number} | Gas: {gas_price_gwei:.2f} Gwei {Style.RESET_ALL}
{Fore.WHITE}==============================================={Style.RESET_ALL}
        """
        print(banner_text)
    except Exception as e:
        print(f"{Fore.RED}Error fetching network status: {e} ❌{Style.RESET_ALL}")
        banner_text = f"""
{Fore.WHITE}==============================================={Style.RESET_ALL}
{Fore.CYAN}                TEA SEPOLIA AUTO BOT{Style.RESET_ALL}
{Fore.YELLOW}     Join Us: https://t.me/AirdropInsiderID {Style.RESET_ALL}
{Fore.YELLOW}     Network status unavailable{Style.RESET_ALL}
{Fore.WHITE}==============================================={Style.RESET_ALL}
        """
        print(banner_text)

def create_providers(proxies):
    providers = []
    if not proxies:
        w3 = Web3(HTTPProvider(network['rpc']))
        providers.append({'provider': w3, 'proxy': 'None'})
    else:
        for proxy in proxies:
            proxy_url = parse_proxy(proxy)
            try:
                # Use proxy only for http; HTTPS RPC bypasses proxy
                proxy_dict = {
                    'http': proxy_url
                }
                w3 = Web3(HTTPProvider(network['rpc'], request_kwargs={'proxies': proxy_dict}))
                # Test connection to ensure proxy works
                w3.eth.get_block_number()
                providers.append({'provider': w3, 'proxy': proxy_url})
            except Exception as e:
                print(f"{Fore.RED}Failed to configure proxy {proxy_url}: {e} ❌{Style.RESET_ALL}")
                continue
    if not providers:
        print(f"{Fore.YELLOW}No valid proxies available. Using direct connection.{Style.RESET_ALL}")
        w3 = Web3(HTTPProvider(network['rpc']))
        providers.append({'provider': w3, 'proxy': 'None'})
    return providers
def connect_to_network():
    try:
        proxies = load_proxies()
        providers = create_providers(proxies)
        private_keys = load_wallets()
        wallets = [{'wallet': Account.from_key(key), 'defaultProvider': providers[0]['provider'], 'proxy': providers[0]['proxy']} for key in private_keys]
        return {'providers': providers, 'wallets': wallets}
    except Exception as e:
        print(f"{Fore.RED}Connection error: {e} ❌{Style.RESET_ALL}")
        sys.exit(1)

def get_wallet_info(wallet_data, index):
    wallet = wallet_data['wallet']
    provider = wallet_data['defaultProvider']
    proxy = wallet_data['proxy']
    address = wallet.address
    try:
        tea_balance = provider.eth.get_balance(address)
    except:
        tea_balance = 0
    try:
        sttea_contract = provider.eth.contract(address=sttea_contract_address, abi=[{"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}])
        sttea_balance = sttea_contract.functions.balanceOf(address).call()
    except:
        sttea_balance = 0
    
    print(f"{Fore.WHITE}\n===== WALLET {index + 1} INFORMATION ====={Style.RESET_ALL}")
    print(f"{Fore.WHITE}Address: {Fore.CYAN}{address} 👤{Style.RESET_ALL}")
    print(f"{Fore.WHITE}TEA Balance: {Fore.CYAN}{provider.from_wei(tea_balance, 'ether')} {network['symbol']} {Style.RESET_ALL}")
    print(f"{Fore.WHITE}stTEA Balance: {Fore.CYAN}{provider.from_wei(sttea_balance, 'ether')} stTEA {Style.RESET_ALL}")
    print(f"{Fore.WHITE}Default proxy: {Fore.CYAN}{proxy} 🌐{Style.RESET_ALL}")
    print(f"{Fore.WHITE}=============================\n{Style.RESET_ALL}")

def with_timeout(func, timeout_ms, error_message):
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout_ms / 1000)
    
    if thread.is_alive():
        raise Exception(error_message)
    if exception[0]:
        raise exception[0]
    return result[0]

def stake_tea(wallet_data, amount, providers):
    max_retries = 3
    last_gas_price = None
    for retry in range(max_retries + 1):
        try:
            provider_info = random.choice(shuffle_array(providers))
            w3 = provider_info['provider']
            proxy = provider_info['proxy']
            wallet = wallet_data['wallet']
            amount_wei = w3.to_wei(amount, 'ether')
            base_gas_price = w3.eth.gas_price
            gas_price = last_gas_price * 120 // 100 if last_gas_price else base_gas_price * 110 // 100
            estimated_gas = 200000
            gas_cost = w3.from_wei(gas_price * estimated_gas, 'ether')
            
            if not confirm_transaction({
                'Action': 'Stake',
                'Amount': f"{amount} TEA",
                'Est. Gas': f"{gas_cost} TEA",
                'Proxy': proxy
            }):
                print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
                print(f"{Fore.WHITE}===== STAKING CANCELED =====\n{Style.RESET_ALL}")
                return None
            
            print(f"{Fore.WHITE}\n===== STAKING TEA ====={Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Staking {amount} TEA for {wallet.address[:6]}...{wallet.address[-4:]} using proxy {proxy} with gas price {w3.from_wei(gas_price, 'gwei')} Gwei...{Style.RESET_ALL}")
            
            nonce = w3.eth.get_transaction_count(wallet.address, 'pending')
            sttea_contract = w3.eth.contract(address=sttea_contract_address, abi=sttea_abi)
            tx = sttea_contract.functions.stake().build_transaction({
                'from': wallet.address,
                'value': amount_wei,
                'gas': estimated_gas,
                'gasPrice': gas_price,
                'nonce': nonce
            })
            
            signed_tx = w3.eth.account.sign_transaction(tx, wallet.key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_hex = w3.to_hex(tx_hash)
            
            print(f"{Fore.WHITE}Transaction sent! Hash: {Fore.CYAN}{tx_hash_hex} 📤{Style.RESET_ALL}")
            print(f"{Fore.WHITE}View on explorer: {network['explorer']}/tx/{tx_hash_hex} 🔗{Style.RESET_ALL}")
            
            show_spinner('Waiting for confirmation...')
            receipt = with_timeout(
                lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60),
                60000,
                'Transaction confirmation timed out after 60 seconds'
            )
            print(f"\r{Fore.GREEN}Transaction confirmed in block {receipt['blockNumber']} ✅{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Successfully staked {amount} TEA! 🎉{Style.RESET_ALL}")
            print(f"{Fore.WHITE}===== STAKING COMPLETED =====\n{Style.RESET_ALL}")
            
            return receipt
        except Exception as e:
            print(f"{Fore.RED}Error staking TEA (attempt {retry + 1}/{max_retries + 1}): {e} ❌{Style.RESET_ALL}")
            if retry < max_retries and ('NONCE_EXPIRED' in str(e) or 'REPLACEMENT_UNDERPRICED' in str(e) or 'timed out' in str(e) or 'rate limit' in str(e)):
                print(f"{Fore.YELLOW}Retrying with a different proxy and higher gas price...{Style.RESET_ALL}")
                last_gas_price = last_gas_price or w3.eth.gas_price
                time.sleep(2)
                continue
            print(f"{Fore.WHITE}===== STAKING FAILED =====\n{Style.RESET_ALL}")
            return None

def withdraw_tea(wallet_data, amount, providers):
    max_retries = 3
    last_gas_price = None
    for retry in range(max_retries + 1):
        try:
            provider_info = random.choice(shuffle_array(providers))
            w3 = provider_info['provider']
            proxy = provider_info['proxy']
            wallet = wallet_data['wallet']
            amount_wei = w3.to_wei(amount, 'ether')
            base_gas_price = w3.eth.gas_price
            gas_price = last_gas_price * 120 // 100 if last_gas_price else base_gas_price * 110 // 100
            estimated_gas = 100000
            gas_cost = w3.from_wei(gas_price * estimated_gas, 'ether')
            
            if not confirm_transaction({
                'Action': 'Withdraw',
                'Amount': f"{amount} stTEA",
                'Est. Gas': f"{gas_cost} TEA",
                'Proxy': proxy
            }):
                print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
                print(f"{Fore.WHITE}===== WITHDRAW CANCELED =====\n{Style.RESET_ALL}")
                return None
            
            print(f"{Fore.WHITE}\n===== WITHDRAWING TEA ====={Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Withdrawing {amount} stTEA for {wallet.address[:6]}...{wallet.address[-4:]} using proxy {proxy} with gas price {w3.from_wei(gas_price, 'gwei')} Gwei...{Style.RESET_ALL}")
            
            nonce = w3.eth.get_transaction_count(wallet.address, 'pending')
            sttea_contract = w3.eth.contract(address=sttea_contract_address, abi=sttea_abi)
            tx = sttea_contract.functions.withdraw(amount_wei).build_transaction({
                'from': wallet.address,
                'gas': estimated_gas,
                'gasPrice': gas_price,
                'nonce': nonce
            })
            
            signed_tx = w3.eth.account.sign_transaction(tx, wallet.key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.    raw_transaction)
            tx_hash_hex = w3.to_hex(tx_hash)
            
            print(f"{Fore.WHITE}Transaction sent! Hash: {Fore.CYAN}{tx_hash_hex} 📤{Style.RESET_ALL}")
            print(f"{Fore.WHITE}View on explorer: {network['explorer']}/tx/{tx_hash_hex} 🔗{Style.RESET_ALL}")
            
            show_spinner('Waiting for confirmation...')
            receipt = with_timeout(
                lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60),
                60000,
                'Transaction confirmation timed out after 60 seconds'
            )
            print(f"\r{Fore.GREEN}Transaction confirmed in block {receipt['blockNumber']} ✅{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Successfully withdrawn {amount} stTEA! 🎉{Style.RESET_ALL}")
            print(f"{Fore.WHITE}===== WITHDRAW COMPLETED =====\n{Style.RESET_ALL}")
            
            return receipt
        except Exception as e:
            print(f"{Fore.RED}Error withdrawing TEA (attempt {retry + 1}/{max_retries + 1}): {e} ❌{Style.RESET_ALL}")
            if retry < max_retries and ('NONCE_EXPIRED' in str(e) or 'REPLACEMENT_UNDERPRICED' in str(e) or 'timed out' in str(e) or 'rate limit' in str(e)):
                print(f"{Fore.YELLOW}Retrying with a different proxy and higher gas price...{Style.RESET_ALL}")
                last_gas_price = last_gas_price or w3.eth.gas_price
                time.sleep(2)
                continue
            print(f"{Fore.WHITE}===== WITHDRAW FAILED =====\n{Style.RESET_ALL}")
            return None

def claim_rewards(wallet_data, providers):
    max_retries = 3
    last_gas_price = None
    for retry in range(max_retries + 1):
        try:
            provider_info = random.choice(shuffle_array(providers))
            w3 = provider_info['provider']
            proxy = provider_info['proxy']
            wallet = wallet_data['wallet']
            
            print(f"{Fore.WHITE}\n===== CLAIMING REWARDS ====={Style.RESET_ALL}")
            base_gas_price = w3.eth.gas_price
            gas_price = last_gas_price * 120 // 100 if last_gas_price else base_gas_price * 110 // 100
            estimated_gas = 100000
            gas_cost = w3.from_wei(gas_price * estimated_gas, 'ether')
            
            if not confirm_transaction({
                'Action': 'Claim Rewards',
                'Est. Gas': f"{gas_cost} TEA",
                'Proxy': proxy
            }):
                print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
                print(f"{Fore.WHITE}===== CLAIM CANCELED =====\n{Style.RESET_ALL}")
                return None
            
            print(f"{Fore.YELLOW}Claiming stTEA rewards for {wallet.address[:6]}...{wallet.address[-4:]} using proxy {proxy} with gas price {w3.from_wei(gas_price, 'gwei')} Gwei...{Style.RESET_ALL}")
            
            nonce = w3.eth.get_transaction_count(wallet.address, 'pending')
            tx = {
                'to': sttea_contract_address,
                'data': '0x3d18b912',
                'gas': estimated_gas,
                'gasPrice': gas_price,
                'nonce': nonce,
                'from': wallet.address
            }
            
            signed_tx = w3.eth.account.sign_transaction(tx, wallet.key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.    raw_transaction)
            tx_hash_hex = w3.to_hex(tx_hash)
            
            print(f"{Fore.WHITE}Transaction sent! Hash: {Fore.CYAN}{tx_hash_hex} 📤{Style.RESET_ALL}")
            print(f"{Fore.WHITE}View on explorer: {network['explorer']}/tx/{tx_hash_hex} 🔗{Style.RESET_ALL}")
            
            show_spinner('Waiting for confirmation...')
            receipt = with_timeout(
                lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60),
                60000,
                'Transaction confirmation timed out after 60 seconds'
            )
            print(f"\r{Fore.GREEN}Transaction confirmed in block {receipt['blockNumber']} ✅{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Successfully claimed rewards! 🎉{Style.RESET_ALL}")
            print(f"{Fore.WHITE}===== CLAIMING COMPLETED =====\n{Style.RESET_ALL}")
            
            balance = w3.eth.get_balance(wallet.address)
            print(f"{Fore.WHITE}Updated TEA Balance: {Fore.CYAN}{w3.from_wei(balance, 'ether')} {network['symbol']} 💰{Style.RESET_ALL}")
            
            return receipt
        except Exception as e:
            print(f"{Fore.RED}Error claiming rewards (attempt {retry + 1}/{max_retries + 1}): {e} ❌{Style.RESET_ALL}")
            if retry < max_retries and ('NONCE_EXPIRED' in str(e) or 'REPLACEMENT_UNDERPRICED' in str(e) or 'timed out' in str(e) or 'rate limit' in str(e)):
                print(f"{Fore.YELLOW}Retrying with a different proxy and higher gas price...{Style.RESET_ALL}")
                last_gas_price = last_gas_price or w3.eth.gas_price
                time.sleep(2)
                continue
            print(f"{Fore.WHITE}===== CLAIMING FAILED =====\n{Style.RESET_ALL}")
            return None

def generate_random_address():
    acct = Account.create()
    return acct.address

def send_to_random_address(wallet_data, amount, providers, skip_confirmation=False, retry_count=0, last_tx_hash=None, last_gas_price=None):
    max_retries = 3
    try:
        provider_info = random.choice(shuffle_array(providers))
        w3 = provider_info['provider']
        proxy = provider_info['proxy']
        wallet = wallet_data['wallet']
        to_address = generate_random_address()
        amount_wei = w3.to_wei(amount, 'ether')
        base_gas_price = w3.eth.gas_price
        gas_price = last_gas_price * 120 // 100 if last_gas_price else base_gas_price * 110 // 100
        estimated_gas = 21000
        gas_cost = w3.from_wei(gas_price * estimated_gas, 'ether')
        
        if last_tx_hash and retry_count > 0:
            try:
                tx_status = w3.eth.get_transaction(last_tx_hash)
                if tx_status and 'blockNumber' not in tx_status:
                    print(f"{Fore.YELLOW}Previous transaction {last_tx_hash} still pending. Increasing gas price...{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}Previous transaction {last_tx_hash} no longer pending. Proceeding...{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error checking transaction {last_tx_hash}: {e}{Style.RESET_ALL}")
        
        if not skip_confirmation:
            if not confirm_transaction({
                'Action': 'Transfer',
                'Amount': f"{amount} TEA",
                'To': f"{to_address[:6]}...{to_address[-4:]}",
                'Est. Gas': f"{gas_cost} TEA",
                'Proxy': proxy
            }):
                print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
                return None
        
        print(f"{Fore.YELLOW}Sending {amount} TEA to random address: {Fore.CYAN}{to_address} from {wallet.address[:6]}...{wallet.address[-4:]} using proxy {proxy} with gas price {w3.from_wei(gas_price, 'gwei')} Gwei 📤{Style.RESET_ALL}")
        
        nonce = w3.eth.get_transaction_count(wallet.address, 'pending')
        tx = {
            'to': to_address,
            'value': amount_wei,
            'gas': estimated_gas,
            'gasPrice': gas_price,
            'nonce': nonce,
            'from': wallet.address
        }
        
        signed_tx = w3.eth.account.sign_transaction(tx, wallet.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.    raw_transaction)
        tx_hash_hex = w3.to_hex(tx_hash)
        
        print(f"{Fore.WHITE}Transaction sent! Hash: {Fore.CYAN}{tx_hash_hex} 🚀{Style.RESET_ALL}")
        print(f"{Fore.WHITE}View on explorer: {network['explorer']}/tx/{tx_hash_hex} 🔗{Style.RESET_ALL}")
        
        show_spinner('Waiting for confirmation...')
        receipt = with_timeout(
            lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60),
            60000,
            'Transaction confirmation timed out after 60 seconds'
        )
        print(f"\r{Fore.GREEN}Transaction confirmed in block {receipt['blockNumber']} ✅{Style.RESET_ALL}")
        
        return {'receipt': receipt, 'toAddress': to_address}
    except Exception as e:
        print(f"{Fore.RED}Error sending TEA (attempt {retry_count + 1}/{max_retries + 1}): {e} ❌{Style.RESET_ALL}")
        if retry_count < max_retries and ('NONCE_EXPIRED' in str(e) or 'REPLACEMENT_UNDERPRICED' in str(e) or 'timed out' in str(e) or 'rate limit' in str(e)):
            print(f"{Fore.YELLOW}Retrying with a different proxy and higher gas price...{Style.RESET_ALL}")
            time.sleep(2)
            return send_to_random_address(wallet_data, amount, providers, skip_confirmation, retry_count + 1, tx_hash_hex if 'tx_hash_hex' in locals() else last_tx_hash, gas_price or base_gas_price)
        print(f"{Fore.YELLOW}Skipping transfer due to failure.{Style.RESET_ALL}")
        return None
    finally:
        time.sleep(1)  # Rate-limit to avoid overwhelming RPC/proxies

def execute_random_transfers(wallets, amount, number_of_transfers, providers, is_daily_task=False):
    print(f"{Fore.WHITE}\n===== BATCH TRANSFER ====={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Preparing {number_of_transfers} random transfers of {amount} TEA each... 🚀{Style.RESET_ALL}")
    
    if not is_daily_task:
        wallet_count = len(wallets) if isinstance(wallets, list) else 1
        gas_price = providers[0]['provider'].eth.gas_price
        estimated_gas = 21000
        gas_cost = providers[0]['provider'].from_wei(gas_price * estimated_gas * number_of_transfers * wallet_count, 'ether')
        
        if not confirm_transaction({
            'Action': 'Batch Transfer',
            'Total Amount': f"{(amount * number_of_transfers * wallet_count):.4f} TEA",
            'Transfers': number_of_transfers * wallet_count,
            'Wallets': wallet_count,
            'Est. Gas': f"{gas_cost} TEA"
        }):
            print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
            print(f"{Fore.WHITE}===== BATCH TRANSFER CANCELED =====\n{Style.RESET_ALL}")
            return []
    
    print(f"{Fore.YELLOW}Starting {number_of_transfers} transfers per wallet...\n{Style.RESET_ALL}")
    
    results = []
    def process_wallet(wallet_data):
        print(f"{Fore.CYAN}\nProcessing transfers for wallet {wallet_data['wallet'].address[:6]}...{wallet_data['wallet'].address[-4:]}{Style.RESET_ALL}")
        for index in range(number_of_transfers):
            print(f"{Fore.WHITE}\nTransfer {index + 1}/{number_of_transfers}{Style.RESET_ALL}")
            result = send_to_random_address(wallet_data, amount, providers, skip_confirmation=True)
            if result:
                results.append(result)
            else:
                print(f"{Fore.YELLOW}Skipping transfer {index + 1} due to failure.{Style.RESET_ALL}")
    
    if isinstance(wallets, list):
        for wallet_data in wallets:
            process_wallet(wallet_data)
    else:
        process_wallet(wallets)
    
    total_transfers = number_of_transfers * (len(wallets) if isinstance(wallets, list) else 1)
    print(f"{Fore.GREEN}\nCompleted {len(results)}/{total_transfers} transfers successfully. 🎉{Style.RESET_ALL}")
    print(f"{Fore.WHITE}===== BATCH TRANSFER COMPLETED =====\n{Style.RESET_ALL}")
    
    return results

def execute_daily_task(wallets, providers):
    amount = 0.0001
    number_of_transfers = 100
    wallet_count = len(wallets) if isinstance(wallets, list) else 1
    
    print(f"{Fore.WHITE}\n===== DAILY TASK ====={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Preparing daily task: {number_of_transfers} transfers of {amount} TEA each for {wallet_count} wallet{'s' if wallet_count > 1 else ''}{Style.RESET_ALL}")
    
    gas_price = providers[0]['provider'].eth.gas_price
    estimated_gas = 21000
    gas_cost = providers[0]['provider'].from_wei(gas_price * estimated_gas * number_of_transfers * wallet_count, 'ether')
    
    if not confirm_transaction({
        'Action': 'Daily Task',
        'Total Amount': f"{(amount * number_of_transfers * wallet_count):.4f} TEA",
        'Transfers': number_of_transfers * wallet_count,
        'Wallets': wallet_count,
        'Est. Gas': f"{gas_cost} TEA"
    }):
        print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
        print(f"{Fore.WHITE}===== DAILY TASK CANCELED =====\n{Style.RESET_ALL}")
        return
    
    execute_random_transfers(wallets, amount, number_of_transfers, providers, is_daily_task=True)
    
    print(f"{Fore.WHITE}===== DAILY TASK COMPLETED =====\n{Style.RESET_ALL}")

def select_wallet(wallets, allow_all=False):
    print(f"{Fore.WHITE}\n===== SELECT WALLET ====={Style.RESET_ALL}")
    for i, wallet_data in enumerate(wallets):
        print(f"{Fore.WHITE}{i + 1}. {wallet_data['wallet'].address[:6]}...{wallet_data['wallet'].address[-4:]}{Style.RESET_ALL}")
    if allow_all:
        print(f"{Fore.WHITE}{len(wallets) + 1}. All wallets{Style.RESET_ALL}")
    print(f"{Fore.WHITE}0. Back to main menu{Style.RESET_ALL}")
    print(f"{Fore.WHITE}===================={Style.RESET_ALL}")
    
    answer = input(f"{Fore.YELLOW}\nSelect wallet number (0{', ' + str(len(wallets) + 1) + ' for all' if allow_all else ''}): {Style.RESET_ALL}")
    try:
        index = int(answer) - 1
        if answer == '0':
            return None
        elif allow_all and int(answer) == len(wallets) + 1:
            return wallets
        elif index < 0 or index >= len(wallets):
            print(f"{Fore.RED}Invalid selection. Please try again. ⚠️{Style.RESET_ALL}")
            return select_wallet(wallets, allow_all)
        return wallets[index]
    except ValueError:
        print(f"{Fore.RED}Invalid selection. Please try again. ⚠️{Style.RESET_ALL}")
        return select_wallet(wallets, allow_all)

def show_main_menu():
    config = load_config()
    network_data = connect_to_network()
    providers = network_data['providers']
    wallets = network_data['wallets']
    
    display_banner(providers[0]['provider'])
    
    for i, wallet_data in enumerate(wallets):
        get_wallet_info(wallet_data, i)
    
    print(f"{Fore.WHITE}\n===== MAIN MENU ====={Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. Send TEA to random addresses{Style.RESET_ALL}")
    print(f"{Fore.WHITE}2. Stake TEA{Style.RESET_ALL}")
    print(f"{Fore.WHITE}3. Claim rewards{Style.RESET_ALL}")
    print(f"{Fore.WHITE}4. Withdraw stTEA{Style.RESET_ALL}")
    print(f"{Fore.WHITE}5. Daily task (100 transfers of 0.0001 TEA){Style.RESET_ALL}")
    print(f"{Fore.WHITE}6. Exit{Style.RESET_ALL}")
    print(f"{Fore.WHITE}===================={Style.RESET_ALL}")
    
    answer = input(f"{Fore.YELLOW}\nChoose an option (1-6): {Style.RESET_ALL}")
    if answer == '6':
        print(f"{Fore.WHITE}\n===== EXITING ====={Style.RESET_ALL}")
        print(f"{Fore.WHITE}Thank you for using TEA BOT! 👋{Style.RESET_ALL}")
        print(f"{Fore.WHITE}===================={Style.RESET_ALL}")
        sys.exit(0)
    
    allow_all = True
    selected_wallets = select_wallet(wallets, allow_all)
    
    if not selected_wallets:
        print("\033[H\033[J", end="")  # Clear screen
        show_main_menu()
        return
    
    if answer == '1':
        handle_random_transfers(selected_wallets, providers)
    elif answer == '2':
        handle_staking(selected_wallets, providers)
    elif answer == '3':
        handle_claiming(selected_wallets, providers)
    elif answer == '4':
        handle_withdrawing(selected_wallets, providers)
    elif answer == '5':
        handle_daily_task(selected_wallets, providers)
    else:
        print(f"{Fore.RED}Invalid option. Please try again. ⚠️{Style.RESET_ALL}")
        show_main_menu()

def handle_random_transfers(selected_wallets, providers):
    print(f"{Fore.WHITE}\n===== RANDOM TRANSFERS ====={Style.RESET_ALL}")
    amount_str = input(f"{Fore.YELLOW}Enter amount of TEA to send in each transfer: {Style.RESET_ALL}")
    try:
        amount = float(amount_str)
        if amount <= 0:
            print(f"{Fore.RED}Invalid amount. Please enter a positive number. ⚠️{Style.RESET_ALL}")
            handle_random_transfers(selected_wallets, providers)
            return
    except ValueError:
        print(f"{Fore.RED}Invalid amount. Please enter a positive number. ⚠️{Style.RESET_ALL}")
        handle_random_transfers(selected_wallets, providers)
        return
    
    count_str = input(f"{Fore.YELLOW}Enter number of transfers to make: {Style.RESET_ALL}")
    try:
        count = int(count_str)
        if count <= 0:
            print(f"{Fore.RED}Invalid count. Please enter a positive integer. ⚠️{Style.RESET_ALL}")
            handle_random_transfers(selected_wallets, providers)
            return
    except ValueError:
        print(f"{Fore.RED}Invalid count. Please enter a positive integer. ⚠️{Style.RESET_ALL}")
        handle_random_transfers(selected_wallets, providers)
        return
    
    execute_random_transfers(selected_wallets, amount, count, providers)
    
    input(f"{Fore.YELLOW}\nPress Enter to return to the main menu...{Style.RESET_ALL}")
    print("\033[H\033[J", end="")  # Clear screen
    show_main_menu()

def handle_staking(selected_wallets, providers):
    print(f"{Fore.WHITE}\n===== STAKING ====={Style.RESET_ALL}")
    amount_str = input(f"{Fore.YELLOW}Enter amount of TEA to stake: {Style.RESET_ALL}")
    try:
        amount = float(amount_str)
        if amount <= 0:
            print(f"{Fore.RED}Invalid amount. Please enter a positive number. ⚠️{Style.RESET_ALL}")
            handle_staking(selected_wallets, providers)
            return
    except ValueError:
        print(f"{Fore.RED}Invalid amount. Please enter a positive number. ⚠️{Style.RESET_ALL}")
        handle_staking(selected_wallets, providers)
        return
    
    if isinstance(selected_wallets, list):
        wallet_count = len(selected_wallets)
        gas_price = providers[0]['provider'].eth.gas_price
        estimated_gas = 200000
        gas_cost = providers[0]['provider'].from_wei(gas_price * estimated_gas * wallet_count, 'ether')
        
        if not confirm_transaction({
            'Action': 'Stake',
            'Total Amount': f"{(amount * wallet_count):.4f} TEA",
            'Wallets': wallet_count,
            'Est. Gas': f"{gas_cost} TEA"
        }):
            print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
            print(f"{Fore.WHITE}===== STAKING CANCELED =====\n{Style.RESET_ALL}")
            return
        
        for wallet_data in selected_wallets:
            print(f"{Fore.CYAN}\nProcessing staking for wallet {wallet_data['wallet'].address[:6]}...{wallet_data['wallet'].address[-4:]}{Style.RESET_ALL}")
            stake_tea(wallet_data, amount, providers)
    else:
        stake_tea(selected_wallets, amount, providers)
    
    input(f"{Fore.YELLOW}\nPress Enter to return to the main menu...{Style.RESET_ALL}")
    print("\033[H\033[J", end="")  # Clear screen
    show_main_menu()

def handle_withdrawing(selected_wallets, providers):
    print(f"{Fore.WHITE}\n===== WITHDRAWING ====={Style.RESET_ALL}")
    amount_str = input(f"{Fore.YELLOW}Enter amount of stTEA to withdraw: {Style.RESET_ALL}")
    try:
        amount = float(amount_str)
        if amount <= 0:
            print(f"{Fore.RED}Invalid amount. Please enter a positive number. ⚠️{Style.RESET_ALL}")
            handle_withdrawing(selected_wallets, providers)
            return
    except ValueError:
        print(f"{Fore.RED}Invalid amount. Please enter a positive number. ⚠️{Style.RESET_ALL}")
        handle_withdrawing(selected_wallets, providers)
        return
    
    if isinstance(selected_wallets, list):
        wallet_count = len(selected_wallets)
        gas_price = providers[0]['provider'].eth.gas_price
        estimated_gas = 100000
        gas_cost = providers[0]['provider'].from_wei(gas_price * estimated_gas * wallet_count, 'ether')
        
        if not confirm_transaction({
            'Action': 'Withdraw',
            'Total Amount': f"{(amount * wallet_count):.4f} stTEA",
            'Wallets': wallet_count,
            'Est. Gas': f"{gas_cost} TEA"
        }):
            print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
            print(f"{Fore.WHITE}===== WITHDRAW CANCELED =====\n{Style.RESET_ALL}")
            return
        
        for wallet_data in selected_wallets:
            print(f"{Fore.CYAN}\nProcessing withdrawal for wallet {wallet_data['wallet'].address[:6]}...{wallet_data['wallet'].address[-4:]}{Style.RESET_ALL}")
            withdraw_tea(wallet_data, amount, providers)
    else:
        withdraw_tea(selected_wallets, amount, providers)
    
    input(f"{Fore.YELLOW}\nPress Enter to return to the main menu...{Style.RESET_ALL}")
    print("\033[H\033[J", end="")  # Clear screen
    show_main_menu()

def handle_claiming(selected_wallets, providers):
    print(f"{Fore.WHITE}\n===== CLAIMING ====={Style.RESET_ALL}")
    if isinstance(selected_wallets, list):
        wallet_count = len(selected_wallets)
        gas_price = providers[0]['provider'].eth.gas_price
        estimated_gas = 100000
        gas_cost = providers[0]['provider'].from_wei(gas_price * estimated_gas * wallet_count, 'ether')
        
        if not confirm_transaction({
            'Action': 'Claim Rewards',
            'Wallets': wallet_count,
            'Est. Gas': f"{gas_cost} TEA"
        }):
            print(f"{Fore.RED}Transaction canceled. 🚫{Style.RESET_ALL}")
            print(f"{Fore.WHITE}===== CLAIM CANCELED =====\n{Style.RESET_ALL}")
            return
        
        for wallet_data in selected_wallets:
            print(f"{Fore.CYAN}\nProcessing claim for wallet {wallet_data['wallet'].address[:6]}...{wallet_data['wallet'].address[-4:]}{Style.RESET_ALL}")
            claim_rewards(wallet_data, providers)
    else:
        claim_rewards(selected_wallets, providers)
    
    input(f"{Fore.YELLOW}\nPress Enter to return to the main menu...{Style.RESET_ALL}")
    print("\033[H\033[J", end="")  # Clear screen
    show_main_menu()

def handle_daily_task(selected_wallets, providers):
    print(f"{Fore.WHITE}\n===== DAILY TASK ====={Style.RESET_ALL}")
    execute_daily_task(selected_wallets, providers)
    
    input(f"{Fore.YELLOW}\nPress Enter to return to the main menu...{Style.RESET_ALL}")
    print("\033[H\033[J", end="")  # Clear screen
    show_main_menu()

if __name__ == '__main__':
    load_dotenv()
    show_main_menu()