# ----------------------------------------------------------------------
#  MAIN PROGRAM - generated by the Rappture Builder
# ----------------------------------------------------------------------
import Rappture
import sys
import numpy as np
from common import *
import glob
import scipy.io
import seaborn as sns
import matplotlib.pyplot as plt

# uncomment these to redirect stdout and stderr
# to files for debugging.
#sys.stderr = open('debug.err', 'w')
#sys.stdout = open('debug.out', 'w')

# open the XML file containing the run parameters
io = Rappture.PyXml(sys.argv[1])

#########################################################
# Get input values from Rappture
#########################################################

# get input value for input.phase(parameters).boolean(newf)
# returns value as string "yes" or "no"
newf = io['input.phase(parameters).boolean(newf).current'].value == 'yes'

# get input value for input.phase(parameters).integer(numsamples)
numsamples = int(io['input.phase(parameters).integer(numsamples).current'].value)

# get input value for input.phase(parameters).group(file).string(model)
model = io['input.phase(parameters).group(file).string(model).current'].value

# get input value for input.phase(parameters).string(path)
dpath = io['input.phase(parameters).string(path)'].value

# get input value for input.phase(parameters).choice(distributionr).label
distribution_radius = io['input.phase(parameters).choice(distributionr).label'].value

#########################################################
#  Add your code here for the main body of your program
#########################################################

if newf:
	f = open('personalized', 'r+')
	f.write(model)
	dpath = 'personalized'
	
class GranularCrystalSurrogate(object):

    """
    A class representing a granular crystal surrogate.

    :param case_dir: The directory containing the trained responses.
    """

    # The directory containing the trained responses
    _case_dir = None

    # The directory corresponding to each output
    _out_dir = None

    # The mean of the inputs (used to scale them)
    _X_mean = None

    # The standard deviation of the inputs (used to scale them)
    _X_std = None

    @property 
    def case_dir(self):
        """
        :getter: The case directory.
        """
        return self._case_dir

    @property 
    def out_dir(self):
        """
        :getter: The list of output directories.
        """
        return self._out_dir

    @property 
    def X_mean(self):
        """
        :getter: The mean of the input.
        """
        return self._X_mean

    @property 
    def X_std(self):
        """
        :getter: The standard deviation of the input.
        """
        return self._X_std

    def __init__(self, case_dir, case='E', ad=1):
        """
        Initialize the object.
        """
        assert os.path.isdir(case_dir)
        self._case_dir = case_dir
        tmp_out = [os.path.join(self.case_dir, 'ex' + case + t) for t in ['MaxValues', 'VelF']]
        out_dir = [os.path.join(tmp_out[0], 'q=' + str(i)) for i in range(3)]
        out_dir += [os.path.join(tmp_out[1], 'q=0')]
        # Sanity check
        for o in out_dir:
            assert os.path.isdir(o)
        self._out_dir = out_dir
        # Load the scalings for the inputs
        self._X_mean = np.load(os.path.join(tmp_out[0], 'X_mean.npy'))
        self._X_std = np.load(os.path.join(tmp_out[0], 'X_std.npy'))
        # For each output, we load all surrogates
        # Returns the derictories of all particles found in directory d
        par_dirs = lambda(d): glob.glob(os.path.join(d, 'p=*'))
        # Returns the number of particles in directory d
        num_par = lambda(d): len(par_dirs(d))
        # Sanity check
        num_par_of_first = num_par(self.out_dir[0])
        for o in self.out_dir[1:]:
            assert num_par_of_first == num_par(o)
        # Load all the particles of each output
        q_models = []
        for o in self.out_dir:
            p_models = []
            for p in par_dirs(o):
                Y_mean = np.load(os.path.join(p, 'Y_mean.npy'))
                Y_std = np.load(os.path.join(p, 'Y_std.npy'))
                model_file = os.path.join(p, 'results', 'case_00001', 'ad_%s' % str(ad).zfill(3), 
                                          'new_model.pcl')
                assert os.path.isfile(model_file)
                print '+ loading:', model_file
                model = load_model(model_file)
                model.Y_mean = Y_mean
                model.Y_std = Y_std
                p_models.append(model)
            q_models.append(p_models)
        self._all_models = q_models

    def predict(self, X):
        """
        Make predictions at ``X``.

        :returns:   A tuple representing the predictive mean and variance of the model.
                    The enumeration is done as follows:
                    samples x particles x outputs
        """
        Z = (X - self.X_mean) / self.X_std
        Y = []
        V = []
        for q in self._all_models:
            YY = []
            VV = []
            for p in q:
                y_scaled, v_scaled = p.predict(Z)
                y = y_scaled * p.Y_std + p.Y_mean
                v = v_scaled * p.Y_std ** 2
                YY.append(y[:, 0])
                VV.append(v[:, 0])
            Y.append(YY)
            V.append(VV)
        Y = np.array(Y).T
        V = np.array(V).T
        return Y, V


if __name__ == '__main__':
    main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ex4_dir =os.path.join(main_dir, 'paper', 'ex4')
    raw_data_dir = os.path.join(ex4_dir, 'raw_data')
    case_dir = os.path.join(ex4_dir, 'cases')
    m = GranularCrystalSurrogate(case_dir, case='R', ad=2)
    with open('out.pcl', 'wb') as fd:
        pickle.dump(m, fd, protocol=pickle.HIGHEST_PROTOCOL)
    with open('out.pcl', 'rb') as fd:
        m = pickle.load(fd)
    in_data = scipy.io.loadmat(os.path.join(raw_data_dir, 'R', 'Rmatrices.mat'))['R']
    R = np.array([d[0] for d in in_data])[:, :, 0]
    if distribution_radius == 'Uniform':
		a =  np.min(R)
		b = np.max(R)
		R = a + np.random.rand(numsamples, R.shape[1]) * (b - a)
    else:
		R = 0.5 * (a + b) + 0.0001 * np.random.randn(numsamples, R.shape[1])
    
    Y, V = m.predict(R)
    #plt.plot(Y[0, :, 3])
    #plt.show()
    out_dir = os.path.join(case_dir, 'R')
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    fig_prefix = os.path.join(out_dir, 'joint_plot')
    for p1 in xrange(Y.shape[1]):
        for p2 in xrange(p1 + 1):
            for q1 in xrange(Y.shape[2]):
                for q2 in xrange(q1 + 1):
                    try:
                        fig_file = fig_prefix + '_p1=' + str(p1).zfill(2) + '_p2=' + str(p2).zfill(2) + '_q1=' + str(q1).zfill(2) + '_q2=' + str(q2).zfill(2) + '.pdf'
                        if os.path.isfile(fig_file):
                            continue
                        sns.jointplot(Y[:, p1, q1], Y[:, p2, q2], kind='hex', color='#4CB391')
                        print '+ writing:', fig_file
                        plt.savefig(fig_file, dpi=300)
                        plt.clf()
                    except:
                        plt.clf()


# spit out progress messages as you go along...
Rappture.Utils.progress(0, "Starting...")
Rappture.Utils.progress(5, "Loading data...")
Rappture.Utils.progress(50, "Half-way there")
Rappture.Utils.progress(100, "Done")

#########################################################
# Save output values back to Rappture
#########################################################


io.close()
sys.exit()
