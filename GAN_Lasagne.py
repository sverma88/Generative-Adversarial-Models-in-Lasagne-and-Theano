'''
   Generative Adversarial Networks toy example, using Theano and Lasagne
   MNIST data is used for the experiments
   Noise for the Generator is drawn from Normal Distribution
   Code follows GAN's pseudocode paper of the original paper but with alternate Loss fucntions
'''



import sys
import argparse
import numpy as np
import theano as th
import theano.tensor as T
import lasagne
import lasagne.layers as LL
import time
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os
import scipy.io

from theano.sandbox.rng_mrg import MRG_RandomStreams



# Argument settings
parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=7)
parser.add_argument('--seed_data', type=int, default=5)
parser.add_argument('--batch_size', type=int, default=128)
args = parser.parse_args()
print(args)


'''
 Xavier initialization of weights in the network,
 you can alternatively use Lasagne.init.GlorotNormal as well

'''
def xavier_init(size_data):
    in_dim = size_data[0]
    xavier_stddev = 1. / np.sqrt(in_dim / 2.)
    return np.random.normal(scale=xavier_stddev, size=size_data).astype("float32")



# fixed random seeds
rng = np.random.RandomState(args.seed)
theano_rng = MRG_RandomStreams(rng.randint(2 ** 18))
lasagne.random.set_rng(np.random.RandomState(rng.randint(2 ** 18)))
#data_rng = np.random.RandomState(args.seed_data)



##### Theano variables fortraining the networks
input_var=T.matrix('input_var')
noise_var=T.matrix('noise')


######loading the dataset ######

data = np.load('mnist.npz')
trainx = np.concatenate([data['x_train'], data['x_valid']], axis=0).astype(th.config.floatX)
nr_batches_train = int(trainx.shape[0]/args.batch_size)



##### function to write images on your disk###
def plot(samples):
    fig = plt.figure(figsize=(4, 4))
    gs = gridspec.GridSpec(4, 4)
    gs.update(wspace=0.05, hspace=0.05)

    for i, sample in enumerate(samples):
        ax = plt.subplot(gs[i])
        plt.axis('off')
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_aspect('equal')
        plt.imshow(sample.reshape(28, 28), cmap='Greys_r')

    return fig




'''
   Sigmoid cross entropy function for logits instead of probabilities
   Similar to tensorflow's api
'''

def sigmoid_cross_entropy_with_logits_v1(logits,value):
    Result = logits*(logits>0) - logits * value + T.log(1+T.exp(-1*T.abs_(logits)))
    return Result



##########building the networks#########

#####Generator Model####
'''
   Composed of only two layers,
   input is noise of dim=100 and generates fake images of dim=784
'''

gen_layers=[LL.InputLayer(shape=(args.batch_size,10**2),input_var=noise_var)]
gen_layers.append(LL.DenseLayer(gen_layers[-1],num_units=128,nonlinearity=lasagne.nonlinearities.rectify,
                         W=xavier_init([100,128])))
gen_layers.append(LL.DenseLayer(gen_layers[-1],num_units=784,
                         W=xavier_init([128,784]),nonlinearity=lasagne.nonlinearities.identity))
gen_layers.append(LL.NonlinearityLayer(gen_layers[-1],nonlinearity=lasagne.nonlinearities.sigmoid))


####Discriminator D(X)######
'''
    Composed of only two layers,
    input is an image of dim=784, and returns logit value (not softmax probability) in the last layer
'''
dis_layers= [LL.InputLayer(shape=(None,28**2),input_var=input_var)]
dis_layers.append(LL.DenseLayer(dis_layers[-1],num_units=128,nonlinearity=lasagne.nonlinearities.rectify,
                            W=xavier_init([784,128])))
dis_layers.append(LL.DenseLayer(dis_layers[-1],num_units=1,
                            W=xavier_init([128,1]),nonlinearity=lasagne.nonlinearities.identity))


########Take out the predictions from the networks

#### Passsing real imageds to the discriminator
D_real=LL.get_output(dis_layers[-1])

#### Passing generator's produced images to the discriminator
D_fake=LL.get_output(dis_layers[-1],LL.get_output(gen_layers[-1],deterministic=False))




#Discriminator Loss functions (Generator is frozen i.e. not updated)

##### On passing real images to the discriminator
D_loss_real=sigmoid_cross_entropy_with_logits_v1(D_real,1)
##### On passing fake images to the discriminator
D_loss_fake=sigmoid_cross_entropy_with_logits_v1(D_fake,0)

#### Taking mean of the two
D_loss=D_loss_real.mean() + D_loss_fake.mean()




#Generator Loss (Discriminator is frozen i.e. not updated)

#### On passing fake images to the discriminator
G_loss_fake=sigmoid_cross_entropy_with_logits_v1(D_fake,1)
G_loss=G_loss_fake.mean()


#Finding Paramters for training
D_theta=LL.get_all_params(dis_layers[-1],trainable=True)
G_theta=LL.get_all_params(gen_layers[-1],trainable=True)


#Updating the paramteres with Adam Optimizer with default parameters
D_solver =lasagne.updates.adam(D_loss,D_theta)
G_solver =lasagne.updates.adam(G_loss,G_theta)


##### Writing Training Functions for the both the networks
D_train_fn=th.function(inputs=[input_var,noise_var],outputs=[D_loss],updates=D_solver)
G_train_fn=th.function(inputs=[noise_var],outputs=[G_loss],updates=G_solver)



i=0

if not os.path.exists('Sunny_Lasagne/'):
    os.makedirs('Sunny_Lasagne/')

for it in range(1000000):
    begin =time.time()


    #### Plotting images from the generator after every 1000 iterations
    if it%1000==0:
        noise = theano_rng.normal(size=(16, 100))
        Generated_Images=LL.get_output(gen_layers[-1],noise)
        #### As output from the network is still a theano expression you have to evaluate it
        Get_Images=th.function([],Generated_Images)
        Actual_Images=Get_Images()
        fig = plot(Actual_Images)
        plt.savefig('Sunny_Lasagne/{}.png'.format(str(i).zfill(3)), bbox_inches='tight')
        i += 1
        plt.close(fig)

    Dis_error=0
    Gen_error=0

    #### Sample noise for the generator and upadte Discriminator's parameters
    Sample_noise_D = theano_rng.normal(size=(args.batch_size, 100))
    Evaluate_noise_D=th.function([],Sample_noise_D)
    Actual_Noise_Value_D=Evaluate_noise_D()
    #### Select random minibatch for real Images
    iteration=np.random.randint(nr_batches_train)
    Dis_error_train=D_train_fn(trainx[iteration*args.batch_size:(iteration+1)*args.batch_size],Actual_Noise_Value_D)


    Dis_error+=np.array(Dis_error_train)

    #### Sample noise for the generator and upadte Generator's parameters
    Sample_noise_G = theano_rng.normal(size=(args.batch_size, 100))
    Evaluate_noise_G=th.function([],Sample_noise_G)
    Actual_Noise_Value_G=Evaluate_noise_G()
    Gen_error=G_train_fn(Actual_Noise_Value_G)


    #### print the losses on the terminal

    if it%1000==0:
        print("Iteration %d, loss_discriminator =%4f, loss_generator =%4f" % (it,Dis_error,np.array(Gen_error)))
        sys.stdout.flush()

