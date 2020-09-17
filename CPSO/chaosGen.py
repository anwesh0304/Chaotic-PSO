import numpy as np
from scipy.integrate import odeint

import numpy as np

class ChaosGenerator () :
######################################################################
# Base class for the chaotic generator
# Contains functions for generating chaotic numbers and subsequently
# evolving the states of the internal generators
######################################################################

    def __init__ (self, oshape, gshape=None, cascade=True, gens=2) :
    ######################################################################
    # Child classes use this constructor to initialise essential parameters
    # and the internal generators
    #
    # > oshape  - Shape that object owner uses
    # > gshape  - Internal shape (per generator) as the chaotic map/flow can
    #           can be muti-dimensional
    # > cascade - If cascade=False, then each point in the (Np, D) matrix
    #           evolves independently of other points according to the map.
    #           For the CPSO, this amounts to having a certain correlation
    #           between the random numbers r1, r2 per iteration of the CPSO
    #           - If cascade=True, then each of the Np particles is connected
    #           to the previous one via the chaotic map. Every dimension is
    #           independent of the other, however!
    # > gens    - Number of independent internal chaotic generators. Two by
    #           default for chaotic pso
    ######################################################################

        self.oshape = oshape

        ######################################################################
        # (Np, D, cdims) --> (D, cdims)
        # where 'cdims' is the number of dimensions of the chaotic map/flow
        #
        # NOTE - By default, if map is single dimensional, then cdims=1 and
        # the last shape value is omitted
        ######################################################################
        self.gshape = (lambda s: s[1:] if cascade else s)(oshape if gshape is None else gshape)
        self.cascade = cascade
        self.gens = gens

        # Creating the list of generators with shape (gens, Np, D, cdims)
        self.cgens = (lambda s:np.array([np.random.random_sample (s) for i in range(gens)]))\
                    (self.gshape)

    def getCgens (self) :
    # Returns a copy of the internal generators
        return np.copy (self.cgens)

    def chaosPoints (self, gno=0) :
    ######################################################################
    # Returns numbers based on the underlying chaotic map/flow and depending
    # on the value of gno
    #
    # > gno - If ==0 means to evolve all generators and return them as a matrix of
    #       shape (gens, Np, D)
    #       - If !=0 means to evolve a particular generator (indexed from 1) rand
    #       return a matrix of shape (Np, D)
    ######################################################################

        if gno != 0 :
            if self.cascade :
                # Evolve per particle
                return np.array ([
                    self.evolve(gno-1) for i in range(self.oshape[0])
                ])
            else :
                return self.evolve(gno-1)
        else :
            # Evolve per generator (independent of 'cascade') --> Recursive call
            return np.array ([
                self.chaosPoints (i+1) for i in range(self.gens)
            ])

    def evolve (self) :
    ######################################################################
    # Action for a particular map/flow is defined in the chaotic child
    # classes. In general, the internal generator state is returned and
    # then they are evolved for one timestep
    ######################################################################
        pass

    def getGen (shape, gentype) :
    # Returns a generator of the given shape and underlying map
        return (lambda s : lambda i : ChaosGenerator.cgen[gentype](s).chaosPoints(i))(shape)


class Logistic (ChaosGenerator) :
######################################################################
# Logistic map --> f(x) = r*x*(1-x)
# r = 4 for full chaos
######################################################################

    def __init__ (self, oshape, cascade=True, r=4, gens=2) :
    ######################################################################
    # > r - logistic bifurcation parameter
    #
    # Rest is defined in the parent class
    ######################################################################

        ChaosGenerator.__init__(self, oshape, None, cascade, gens)
        self.r = r

    def evolve (self, gind) :
        # Copying is necessary
        ret = np.copy (self.cgens[gind])
        self.cgens[gind] = (lambda r,x : r*x*(1-x))(self.r, self.cgens[gind])
        return ret

class Tent (ChaosGenerator) :
######################################################################
# Tent map --> f(x) = 2*x , x <= 0.5 ; 2*(1-x) , x > 0.5
# mu = 0.49999 in the equivalent form for numerical stability
######################################################################
    def __init__ (self, oshape, cascade=True, mu=0.49999, gens=2) :
    ######################################################################
    # > mu - Tent bifurcation paramater
    #
    # Rest is defined in the parent class
    ######################################################################
        ChaosGenerator.__init__(self, oshape, None, cascade, gens)
        self.mu = mu

    def evolve (self, gind) :
        # Copying is necessary
        ret = np.copy (self.cgens[gind])
        self.cgens[gind] = (lambda mu,x : np.where(x <= mu, x/mu, (1-x)/(1-mu)))\
                            (self.mu, self.cgens[gind])
        return ret

class Lorenz (ChaosGenerator) :
######################################################################
# Lorenz flow -->   xdot = sigma*(y-x)
#                   ydot = x*(rho-z) - y
#                   zdot = x*y - beta*z
# sigma, beta, rho = 10, 8/3, 28
# lims is a dictonary containing {(sigma, beta, rho) : limits(3,2)} pairs
######################################################################
    lims = {}

    def lorenz (X, t, sigma, beta, rho) :
    # lorenz differential equation needed by scipy odeint
        x, y, z = X
        dXdt = [sigma*(y-x), x*(rho-z) - y, x*y - beta*z]
        return dXdt

    def setLimits (params) :
    ######################################################################
    # No need to recalculate limits of the lorenz flow everytime for the
    # same set of parameters
    ######################################################################
        if params not in Lorenz.lims :
            Lorenz.lims[params] = (lambda s:np.array([
                [np.min(s[:,i]), np.max(s[:,i])] for i in [0, 1, 2]
            ]))\
            (odeint (Lorenz.lorenz, np.random.rand(3), np.linspace (0, 9999, 999999), args = params))
            # Argument to lambda - (Time series of lorenz flow in all three dimensions)


    def __init__ (self, oshape, cascade=True, params=(10, 8.0/3, 28), comp=0, h=0.01, gens=2) :
    ######################################################################
    # > params  - (sigma, beta, rho) of lorenz parameters
    # > comp    - which cdim to consider for chaotic numbers
    # > h       - Time step of evolution
    #
    # Rest is defined in the parent class
    ######################################################################

        ChaosGenerator.__init__ (self, oshape, oshape+(3,), cascade, gens)
        self.params = params
        self.comp = comp
        self.h = h

        # Set limits if not set already
        Lorenz.setLimits (params)

        for i in range(0, self.gens) :
        # Per generator
            for j in [0, 1, 2] :
            # Per dimension of lorenz flow
                self.cgens[i,...,j] = (lambda st,mn,mx : mn + (mx - mn)*st)\
                                    (self.cgens[i,...,j], Lorenz.lims[params][j,0], Lorenz.lims[params][j,1])
                # Argument to lambda - (ith generator jth cdim, min of jth cdim, max of jth cdim)

    def evolveT (self, gind, T=1) :
    # Evolves the lorenz map for T timesteps and sets the internal generator

        for pt in np.ndindex(self.gshape[:-1]) :
        # Per index in (Np, D)
            self.cgens[gind][pt] = odeint(Lorenz.lorenz, self.cgens[gind][pt],
                                          np.arange(0,self.h*(T+1),self.h), args=self.params)[-1]

    def evolve (self, gind) :
    # Evolves the internal generators 1 timestep

        ######################################################################
        # If the limits defined in the dict 'lims' are exceeded, then
        # corresponding chaotic points are replaced with eps or (1-eps) depending
        # on whether its exceeding below or above, respectively
        ######################################################################
        eps = 1e-5

        # Copying is not necessary as it is being scaled
        ret = (lambda n2 : np.where (n2 > 1, 1-eps, n2))(
            (lambda n1 : np.where (n1 < 0, eps, n1))(
            (lambda st, mn, mx : (st - mn)/(mx - mn))
            (self.cgens[gind,...,self.comp],
             Lorenz.lims[self.params][self.comp,0],
             Lorenz.lims[self.params][self.comp,1])
            ))

        self.evolveT (gind)
        return ret

# Used by CPSO for generating swarms
ChaosGenerator.cgen = {
"Log" : Logistic,
"Lor" : Lorenz,
"Tent" : Tent
}