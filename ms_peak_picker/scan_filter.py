import numpy as np

from .utils import Base
from .fticr_denoising import denoise as fticr_remove_baseline

try:
    basestring
except NameError:
    from six import string_types as basestring


#: Global register of all named scan filters
filter_register = {}


def register(name, *args, **kwargs):
    """Decorate a class to register a name for
    it, optionally with a set of associated initialization
    parameters.

    Parameters
    ----------
    name : str
        The name to register the filter under.
    *args
        Positional arguments forwarded to the decorated class's
        initialization method
    **kwargs
        Keyword arguments forwarded to the decorated class's
        intialization method

    Returns
    -------
    function
        A decorating function which will carry out the registration
        process on the decorated class
    """
    def wrap(cls):
        filter_register[name] = cls(*args, **kwargs)
        return cls
    return wrap


class FilterBase(Base):
    """A base type for Filters over raw signal arrays.

    All subtypes should provide a :meth:`filter` method
    which takes arguments *mz_array* and *intensity_array*
    which will be NumPy Arrays.
    """
    def filter(self, mz_array, intensity_array):
        return mz_array, intensity_array

    def __call__(self, mz_array, intensity_array):
        return self.filter(mz_array, intensity_array)


@register("median")
class MedianIntensityFilter(FilterBase):
    """Filter signal below the median signal
    """
    def filter(self, mz_array, intensity_array):
        mask = intensity_array < np.median(intensity_array)
        intensity_array = np.array(intensity_array)
        intensity_array[mask] = 0.
        return mz_array, intensity_array


@register("mean_below_mean")
class MeanBelowMeanFilter(FilterBase):
    """Filter signal below the mean below the mean
    """
    def filter(self, mz_array, intensity_array):
        mean = intensity_array.mean()
        mean_below_mean = (intensity_array < mean).mean()
        mask = intensity_array < mean_below_mean
        intensity_array[mask] = 0.
        return mz_array, intensity_array


@register("savitsky_golay")
class SavitskyGolayFilter(FilterBase):
    """Apply :ref:`Savitsky-Golay smoothing <https://en.wikipedia.org/wiki/Savitzky%E2%80%93Golay_filter>`
    to the signal.

    Attributes
    ----------
    deriv : int
        Number of derivatives to take
    polyorder : int
        Order of the polynomial to construct
    window_length : int
        Number of data points to include around the current point
    """
    def __init__(self, window_length=5, polyorder=3, deriv=0):
        self.window_length = window_length
        self.polyorder = polyorder
        self.deriv = deriv

    def filter(self, mz_array, intensity_array):
        from scipy.signal import savgol_filter
        smoothed = savgol_filter(
            intensity_array, window_length=self.window_length,
            polyorder=self.polyorder, deriv=self.deriv).clip(0)
        mask = smoothed > 0
        return mz_array[mask], smoothed[mask]


@register("tenth_percent_of_max")
@register("one_percent_of_max", p=0.01)
class NPercentOfMaxFilter(FilterBase):
    def __init__(self, p=0.001):
        self.p = p

    def filter(self, mz_array, intensity_array):
        mask = (intensity_array / intensity_array.max()) < self.p
        intensity_array_clone = np.array(intensity_array)
        intensity_array_clone[mask] = 0.
        return mz_array, intensity_array_clone


@register("fticr_baseline")
class FTICRBaselineRemoval(FilterBase):
    """Apply FTICR baseline removal.

    This calls :py:func:`~ms_peak_picker.fticr_denoising.denoise`

    Attributes
    ----------
    region_width : float
        The width of the region to group windows
        by.
    scale : float
        The multiplier of the noise level to remove.
    window_length : float
        The size of the window to tile across each
        region

    See Also
    --------
    ms_peak_picker.fticr_denoising.denoise
    """
    def __init__(self, window_length=1., region_width=10, scale=5):
        self.window_length = window_length
        self.region_width = region_width
        self.scale = scale

    def filter(self, mz_array, intensity_array):
        return fticr_remove_baseline(mz_array, intensity_array, self.window_length, self.region_width, self.scale)


@register("linear_resampling", 0.01)
class LinearResampling(FilterBase):
    def __init__(self, spacing):
        self.spacing = spacing

    def filter(self, mz_array, intensity_array):
        lo = mz_array.min()
        hi = mz_array.max()
        new_mz = np.arange(lo, hi + self.spacing, self.spacing)
        new_intensity = np.interp(new_mz, mz_array, intensity_array)
        return new_mz, new_intensity


@register("over_10", 10)
@register("over_100", 100)
class ConstantThreshold(FilterBase):
    def __init__(self, constant):
        self.constant = constant

    def filter(self, mz_array, intensity_array):
        mask = intensity_array > self.constant
        return mz_array[mask], intensity_array[mask]


@register("extreme_scale_limiter", 30e3)
class MaximumScaler(FilterBase):
    def __init__(self, threshold):
        self.threshold = threshold

    def filter(self, mz_array, intensity_array):
        if intensity_array.max() > self.threshold:
            intensity_array = intensity_array / intensity_array.max() * self.threshold
        return mz_array, intensity_array


def transform(mz_array, intensity_array, filters=None):
    """Apply a series of *filters* to the paired m/z and intensity
    arrays.

    The `filters` argument should be an iterable of either strings,
    callables, or instances of :class:`FilterBase`-derived classes.
    If they are strings, they must be registered names, as created by
    :func:`register`.

    Parameters
    ----------
    mz_array : np.ndarray[float64]
        The m/z array to filter
    intensity_array : np.ndarray[float64]
        The intensity array to filter
    filters : Iterable
        An Iterable of either strings, callables, or instances
        of :class:`FilterBase`-derived classes. If they are
        strings, they must be registered names, as created by
        :func:`register`

    Returns
    -------
    np.ndarray[float64]:
        The m/z array after filtering
    np.ndarray[float64]:
        The intensity array after filtering
    """
    if filters is None:
        filters = []

    for filt in filters:
        if isinstance(filt, basestring):
            filt = filter_register[filt]
        mz_array, intensity_array = filt(mz_array, intensity_array)

    return mz_array, intensity_array
