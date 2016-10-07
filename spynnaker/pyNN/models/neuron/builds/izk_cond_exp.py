from spynnaker.pyNN.models.neuron.builds.abstract_neuron_build \
    import AbstractNeuronBuild
from spynnaker.pyNN.models.pyNN_model import pyNN_model
from spynnaker.pyNN.models.neuron.input_types.input_type_conductance \
    import InputTypeConductance
from spynnaker.pyNN.models.neuron.neuron_models.neuron_model_izh \
    import NeuronModelIzh
from spynnaker.pyNN.models.neuron.synapse_types.synapse_type_exponential \
    import SynapseTypeExponential
from spynnaker.pyNN.models.neuron.threshold_types.threshold_type_static \
    import ThresholdTypeStatic


@pyNN_model
class IzkCondExp(AbstractNeuronBuild):

    max_atoms_per_core = 255

    neuron_model = NeuronModelIzh
    synapse_type = SynapseTypeExponential
    input_type = InputTypeConductance
    threshold_type = ThresholdTypeStatic

    binary_name = "IZK_cond_exp.aplx"
