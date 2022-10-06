# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 13:08:54 2022

@author: u176198
"""
import pandas as pd
import math
import random



results=pd.DataFrame(data={"dailyExpectedVol":[],
                           "alpha":[],
                           "vaultLazyConvert":[],
                           "vaultFutures":[],
                           "AMM":[],
                           "HODL":[],
                           "finalPrice":[]})


r0start=185000000
r1start=120000
numBlocksPerDay=50
numDaysSimulation=365
blocksForSim=numBlocksPerDay*numDaysSimulation
diffusionBlocks=50
numberOfSimsPerCombination=500
"""0.0003 is equiv to 1% TVL trading in a 0.3% fee pool"""
dailyFeesVsK=0.000

def vaultFuturesStrategy(r0,r1,price,netVault0,netVault1,block,kStart,activeFuturePositions,diffusionBlocks,alpha):
    
    r0new=math.sqrt(price*r0*r1)
    r1new=r0new/price
    
    vault0,vault1=0,0
    """"(r1-r1new)>0 means the token 1 has increased in value"""
    if (r1-r1new)>0:

        vault1=vault1+(r1-r1new)*(alpha)
        """"repay the arbitrageur"""
        r0=r0new+(r0-r0new)*(alpha)
        """"rebalance the pool"""
        r1=r0/price
        vault1=vault1+(r1new-r1)
    else:
        vault0=vault0+(r0-r0new)*(alpha)
        """"repay the arbitrageur"""
        r1=r1new+(r1-r1new)*(alpha)
        r0=r1*price
        vault0=vault0+(r0new-r0)
    """settles (1/diffusionBlocks) of the active futures contracts"""
    if block % diffusionBlocks==0:
        for i in range(0,diffusionBlocks):
            valueToBeAdded=activeFuturePositions[i][0]*(price-activeFuturePositions[i][1])
            r0ValueAdd=(valueToBeAdded/2)
            r1ValueAdd=(valueToBeAdded/2)/price
            r0=r0+r0ValueAdd
            r1=r1+r1ValueAdd
        kStart=r0*r1
    if vault0<vault1*price:
        """ this implies price has gone up """
        """apply rebalancing fee to the amount needed to be rebalance, in token1 s"""
        vault1Additional=(vault1-(vault0/price))
        """creates a buy futures contract against the block producer"""
        activeFuturePositions[sim%diffusionBlocks]=[vault1Additional/2,price]
        vault0=vault0+(vault1Additional/2)*price
        vault1=(vault1-vault1Additional/2)
        r0=r0+(vault0)
        r1=r1+(vault1)
        newK=r0*r1
        kOverNewK=math.sqrt(kStart/newK)
        netVault0=netVault0+r0*(1-kOverNewK)
        netVault1=netVault1+r1*(1-kOverNewK)
        """Keep the constant constant between blocks"""
        r0=r0*kOverNewK
        r1=r1*kOverNewK
        vault0=0
        vault1=0
    else:
        """ this implies price has gone down """
        """apply rebalancing fee to the amount needed to be rebalance"""
        vault0Additional=(vault0-vault1*price)
        """creates a sell futures contract against the block producer (minus sign) """
        activeFuturePositions[sim%diffusionBlocks]=[-(vault0Additional/2)/price,price]
        vault1=vault1+(vault0Additional/2)/price
        vault0=(vault0-vault0Additional/2)
        r0=r0+(vault0)
        r1=r1+(vault1)
        newK=r0*r1
        kOverNewK=math.sqrt(kStart/newK)
        netVault0=netVault0+r0*(1-kOverNewK)
        netVault1=netVault1+r1*(1-kOverNewK)
        """Keep the constant constant between blocks"""
        r0=r0*kOverNewK
        r1=r1*kOverNewK
    return r0,r1,netVault0,netVault1,kStart,activeFuturePositions

def vaultLazyConversionStrategy(r0,r1,price,vault0,vault1,block,diffusionBlocks,alpha):
    r0new=math.sqrt(price*r0*r1)
    r1new=r0new/price
    """"(r1-r1new)>0 means the token 1 has increased in value"""
    if (r1-r1new)>0:
        vault1=vault1+(r1-r1new)*(alpha)
        """"repay the arbitrageur"""
        r0=r0new+(r0-r0new)*(alpha)
        """"rebalance the pool"""
        r1=r0/price
        vault1=vault1+(r1new-r1)
        
    else:
        vault0=vault0+(r0-r0new)*(alpha)

        """"repay the arbitrageur"""
        r1=r1new+(r1-r1new)*(alpha)
        r0=r1*price
        vault0=vault0+(r0new-r0)
        
        
    """performs the conversion every diffusionBlocks"""
    if block % diffusionBlocks==0:
        if vault0<vault1*price:
            
            """ this implies price has gone up """
            vault1Additional=(vault1-(vault0/price))
            vault0=vault0+(vault1Additional/2)*price
            vault1=(vault1-vault1Additional/2)
            r0=r0+(vault0)
            r1=r1+(vault1)
            vault0=0
            vault1=0
        else:
            """ this implies price has gone down """
            """apply rebalancing fee to the amount needed to be rebalance"""
            vault0Additional=(vault0-vault1*price)
            vault1=vault1+(vault0Additional/2)/price
            vault0=(vault0-vault0Additional/2)
            r0=r0+(vault0)
            r1=r1+(vault1)
            vault0=0
            vault1=0
    return r0,r1,vault0,vault1

def addTXFees(r0,r1,transactionFee):
    return r0*(1+transactionFee),r1*(1+transactionFee)

for dailyExpectedVol in [1.1]:
    for alpha in [0.95]:
        rebalalanceThresholds=[0]
        for rebalanceThreshold in rebalalanceThresholds:
            rebalanceFee=0
            
            for sim in range(0,numberOfSimsPerCombination):
                price=r0start/r1start
                
                """Futures Strategy Variables"""
                netVault0Futs=0
                netVault1Futs=0
                r0Futs=r0start
                r1Futs=r1start
                kStartFuts=r0Futs*r1Futs
                
                """Lazy Conversion Strategy Variables"""
                r0Lazy=r0start
                r1Lazy=r1start
                vault0Lazy=0
                vault1Lazy=0  
                
                activeFuturePositions=[[0,0] for i in range(0,diffusionBlocks)]
                for block in range(0,blocksForSim):
                    """ **(2*random.random()) introduces a vol of vol"""
                    perBlockVol=(dailyExpectedVol+(dailyExpectedVol-1)*(random.random()-0.5))**(1/numBlocksPerDay)
                    if random.random()>0.5:
                        price=price*(perBlockVol)
                    else:
                        price = price/perBlockVol
                        
                    r0Futs,r1Futs,netVault0Futs,netVault1Futs,kStartFuts,activeFuturePositions=vaultFuturesStrategy(r0Futs,r1Futs,price,netVault0Futs,netVault1Futs,block,kStartFuts,activeFuturePositions,diffusionBlocks,alpha)
                    r0Lazy,r1Lazy,vault0Lazy,vault1Lazy=vaultLazyConversionStrategy(r0Lazy,r1Lazy,price,vault0Lazy,vault1Lazy,block,diffusionBlocks,alpha)
                    
                    r0Lazy,r1Lazy=addTXFees(r0Lazy,r1Lazy,dailyFeesVsK/numBlocksPerDay)
                    r0Futs,r1Futs=addTXFees(r0Futs,r1Futs,dailyFeesVsK/numBlocksPerDay)
                
                vaultStrategyValueFuts=(r1Futs+netVault1Futs)*price + r0Futs+netVault0Futs
                vaultStrategyValueLazy=(r1Lazy+vault1Lazy)*price + r0Lazy+vault0Lazy
                
                results=results.append({"dailyExpectedVol":dailyExpectedVol,
                                           "alpha":alpha,
                                           "finalPrice": price,
                                           "vaultLazyConvert":vaultStrategyValueLazy,
                                           "vaultFutures":vaultStrategyValueFuts,
                                           "AMM":(math.sqrt(r0start*r1start*price)+math.sqrt(r0start*r1start/price)*price)*(1+dailyFeesVsK/numBlocksPerDay)**numberOfSimsPerCombination,
                                           "HODL":r0start+r1start*price},ignore_index=True)
results.to_csv('C:/Users/U176198/Documents/PhD/Projects/LVR/LVR.csv')  
print("protocol values", results[["vaultLazyConvert","vaultFutures","AMM","HODL"]].describe())