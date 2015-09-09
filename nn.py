import numpy as np

class NeuralNetwork(object):
    def __init__(self, input_size, dim, networkID):
        self.dim = [input_size]+list(dim)
        try:
            self.weight_matrix = np.load(str(networkID)+'.npy')
        except:
            self.weight_matrix = []
            weight_layer = np.random.rand(self.dim[1],self.dim[0])
            self.weight_matrix.append(weight_layer)
            for a,b in zip(self.dim[1:-1], self.dim[2:]):
                weight_layer = np.random.random((b,a+1))
                self.weight_matrix.append(weight_layer)


    def activate(self, inputs):
        activations = []
        v = inputs
        # v.append(1)
        for w in self.weight_matrix:
            x = np.dot(w,v)
            v = self.activation_function(x)
            v = np.append(v,[1])
            activations.append(v)
        return activations

    def save(self):
        np.save(str(networkID)+'.npy', self.weight_matrix)

    def print_weights(self):
        for w in self.weight_matrix:
            print(w)

    @staticmethod
    def activation_function(x):
        return np.tanh(x)
