# Use HMM to Classify the time series into bull, bear, shake.
# As signals for broker, to make desicion.

# GAN_Generator
#   input0: multi-dimension confirmed data
#   input1: trend comes form HMM

# GAN_Discriminator
#   fix a period like 5 tradedays
#   Cal the profit
