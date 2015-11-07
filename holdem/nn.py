import numpy as np
import os

class NeuralNetwork(object):
    SAVE_DIR = os.getcwd() + '/data/'
    def __init__(self, dim, networkID, slope = 0.1):
        self.networkID = networkID
        self.dim = list(dim)
        self.num_layers = len(self.dim)
        self.slope = slope
        try:
            self.weights = np.load(NeuralNetwork.SAVE_DIR + str(networkID)+'_weights.npy')
            self.biases = np.load(NeuralNetwork.SAVE_DIR + str(networkID)+'_biases.npy')
        except:
            self.weights = [np.random.randn(y,x)/np.sqrt(x) for x,y in zip(self.dim[:-1], self.dim[1:])]
            self.biases = [np.random.randn(y,1) for y in self.dim[1:]]

    def activate(self, inputs):
        a = np.array([inputs]).transpose()
        assert a.shape == (self.dim[0],1)
        for b, w in zip(self.biases, self.weights):
            a = NeuralNetwork.sigmoid(np.dot(w,a)+b, self.slope)
        return a

    def save(self):
        np.save(NeuralNetwork.SAVE_DIR + str(self.networkID)+'_weights.npy', self.weights)
        np.save(NeuralNetwork.SAVE_DIR + str(self.networkID)+'_biases.npy', self.biases)

    def delete(self):
        os.remove(NeuralNetwork.SAVE_DIR + str(self.networkID)+'_weights.npy')
        os.remove(NeuralNetwork.SAVE_DIR + str(self.networkID)+'_biases.npy')

    def print_weights(self):
        for w in self.weights:
            print(w)

    def update_weights(self, inputs, target_output, rate):
        nabla_b, nabla_w = self.backpropogate(inputs, target_output)
        self.biases = [b + (-rate)*nb for b, nb in zip(self.biases, nabla_b)]
        self.weights = [w + (-rate)*nw for w, nw in zip(self.weights, nabla_w)]

    def backpropogate(self, inputs, target_output):
        nabla_b = [np.zeros(b.shape) for b in self.biases]
        nabla_w = [np.zeros(w.shape) for w in self.weights]

        # feedforward
        activation = np.array([inputs]).transpose()
        activations = [inputs]
        nabla_w = [np.zeros(w.shape) for w in self.weights]
        nets = []
        for b, w in zip(self.biases, self.weights):
            net = np.dot(w, activation) + b
            nets = np.append(nets, net)
            activation = NeuralNetwork.sigmoid(net, self.slope)
            activations = np.append(activations, activation)
        # implemented from notes: http://neuralnetworksanddeeplearning.com/chap2.html
        # backward
        delta = (activations[-1]-target_output)*NeuralNetwork.sigmoid_prime(nets[-1], self.slope)
        nabla_b[-1] = delta
        nabla_w[-1] = np.dot(delta, activations[-2].transpose())
        # nabla_w[-1] = np.dot(delta, activations[-2])

        for l in range(2, self.num_layers):
            net = nets[-l]
            sp = NeuralNetwork.sigmoid_prime(net, self.slope)
            # delta = np.dot(np.dot(delta, np.array(self.weights[-l+1])), np.diag(list(sp)))
            delta = np.dot(np.array(self.weights[-l+1]).transpose(), delta)*sp
            nabla_b[-l] = delta
            nabla_w[-l] = np.dot(delta, activations[-l-1].transpose())
        return (nabla_b, nabla_w)

    def quadratic_error(self, inputs, target_output):
        return 0.5*np.linalg.norm(self.activate(inputs)-target_output)**2

    @staticmethod
    def sigmoid(x, slope):
        return np.tanh(slope*x)

    @staticmethod
    def sigmoid_prime(x, slope):
        return slope*(1- (np.tanh(slope*x)**2))
