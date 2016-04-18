cdef class FittedPeak(object):
    cdef:
        public double mz
        public double intensity
        public double signal_to_noise
        public double full_width_at_half_max
        public double left_width
        public double right_width
        public long peak_count
        public long index
        public double area

    cpdef bint _eq(self, FittedPeak other)

cdef class PeakSet(object):
    cdef:
        public tuple peaks

    cdef FittedPeak _get_nearest_peak(self, double mz, double* errout)

    cdef FittedPeak _has_peak(self, double mz, double tolerance=*)

    cdef PeakSet _between(self, double m1, double m2)

    cdef FittedPeak getitem(self, size_t i)

    cdef size_t _get_size(self)


cpdef FittedPeak binary_search_ppm_error(tuple array, double value, double tolerance)
cdef FittedPeak _binary_search_ppm_error(tuple array, double value, size_t lo, size_t hi, double tolerance)
cdef FittedPeak _binary_search_nearest_match(tuple array, double value, size_t lo, size_t hi, double* errout)

