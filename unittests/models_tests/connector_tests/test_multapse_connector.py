#!/usr/bin/env python
import unittest
import spynnaker.pyNN as pynn
from pprint import pprint as pp
populations = list()
cell_params_lif = {
    'cm'  : 0.25, 
    'i_offset'  : 0.0,
    'tau_m'     : 20.0,
    'tau_refrac': 2.0,
    'tau_syn_E' : 5.0,
    'tau_syn_I' : 5.0,
    'v_reset'   : -70.0,
    'v_rest'    : -65.0,
    'v_thresh'  : -50.0
                     }
pynn.setup(timestep=1,min_delay = 1, max_delay = 10)
populations.append(pynn.Population(5,pynn.IF_curr_exp,cell_params_lif,label="First normal pop" ))
populations.append(pynn.Population(10,pynn.IF_curr_exp,cell_params_lif,label="Second normal pop" ))
weight , delay = 5, 5
projections= list()
class MultapseConnectorTest(unittest.TestCase):
    def test_a(self):
        pynn.Projection(populations[0],populations[1],pynn.MultapseConnector(
            num_synapses=5, weights= weight, delays= delay ))

    def test_nasty(self):
        pynn.Projection(populations[0],populations[0],pynn.MultapseConnector(
            num_synapses=10,weights= weight,delays= delay))

    def test_generate_synaptic_list(self):
        number_of_neurons = 5
        first_population=pynn.Population(number_of_neurons,pynn.IF_curr_exp,cell_params_lif,label="One pop")
        second_population=pynn.Population(number_of_neurons,pynn.IF_curr_exp,cell_params_lif,label= "Second pop")
        weight = 2
        delay = 1
        synapse_type = first_population._vertex.get_synapse_id('excitatory')
        connection = pynn.MultapseConnector(1,weight,delay)
        synaptic_list = connection.generate_synapse_list(first_population._vertex,first_population._vertex,1,synapse_type)
        pp(synaptic_list.get_rows())


if __name__ == "__main__":
        unittest.main()