from spynnaker.pyNN.models.neuron.neuron_models\
    .neuron_model_leaky_integrate_and_fire \
    import NeuronModelLeakyIntegrateAndFire
from spynnaker.pyNN.models.pyNN_model import pyNN_model
from spynnaker.pyNN.models.neuron.builds.abstract_neuron_build \
    import AbstractNeuronBuild
from spynnaker.pyNN.models.neuron.synapse_types.synapse_type_exponential \
    import SynapseTypeExponential
from spynnaker.pyNN.models.neuron.input_types.input_type_current \
    import InputTypeCurrent
from spynnaker.pyNN.models.neuron.threshold_types.threshold_type_static \
    import ThresholdTypeStatic


@pyNN_model
class IFCurrExp(AbstractNeuronBuild):
    """ Leaky integrate and fire neuron with an exponentially decaying \
        current input
    """

    max_atoms_per_core = 255

    neuron_model = NeuronModelLeakyIntegrateAndFire
    synapse_type = SynapseTypeExponential
    input_type = InputTypeCurrent
    threshold_type = ThresholdTypeStatic

    binary_name = "IF_curr_exp.aplx"
