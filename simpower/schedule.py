"""
Time and schedule related models.
"""

from datetime import timedelta, datetime as dt
from .commonscripts import *
from operator import attrgetter
import logging


def get_schedule(filename):
    return ts_from_csv(filename)


def make_times_basic(N):
    """make a :class:`schedule.TimeIndex` of N times with hourly interval"""
    # 使用当前日期作为起始点，避免只有一个时间点的问题
    start_date = dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = date_range(start=start_date, periods=N, freq="H")
    return TimeIndex(dates)


def just_one_time():
    """make a TimeIndex with just one time in it"""
    return make_times_basic(1)


def make_constant_schedule(times, power=0):
    # 确保使用列表形式的索引
    return Series(power, index=times.strings.values)


class TimeIndex(object):

    """a list of times (underlying model is pandas.Index)"""

    def __init__(self, index, str_start=0):
        strings = ["t%02d" % (i + str_start) for i in range(len(index))]
        # 确保index是日期时间对象
        if isinstance(index, pd.Index):
            # 检查是否为日期时间索引
            if hasattr(index, 'dtype') and pd.api.types.is_datetime64_any_dtype(index.dtype):
                self.times = index.copy()
            else:
                # 尝试转换为日期时间索引
                try:
                    self.times = pd.DatetimeIndex(index)
                except:
                    # 如果无法转换，创建一个默认的日期时间索引
                    logging.warning("无法将索引转换为日期时间索引，使用默认日期")
                    start_date = dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    self.times = pd.date_range(start=start_date, periods=len(index), freq="H")
        else:
            # 如果不是索引对象，尝试转换
            try:
                self.times = pd.DatetimeIndex(index)
            except:
                logging.warning("无法将输入转换为日期时间索引，使用默认日期")
                start_date = dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
                self.times = pd.date_range(start=start_date, periods=len(index), freq="H")
        
        self.strings = Series(strings, index=self.times)
        self._set = self.strings.values.tolist()

        self.get_interval()
        
        # 处理空的DatetimeIndex
        if len(self.times) > 0:
            self.Start = self.times[0]
            self.End = self.times[-1] + self.interval
        else:
            # 如果时间索引为空，设置默认值
            self.Start = pd.Timestamp('2000-01-01')
            self.End = self.Start
            self.interval = pd.Timedelta(hours=1)
            
        self.startdate = self.Start.date()
        self.span = self.End - self.Start
        self.spanhrs = hours(self.span)

        self.set_initial()

        self._int_overlap = 0
        self._int_division = len(self)
        self._str_start = str_start

    def set_initial(self, initialTime=None):
        if initialTime:
            self.initialTime = initialTime
        else:
            self.initialTime = pd.Timestamp(self.Start - self.interval)
            self.initialTime.index = "Init"
        self.initialTimestr = "tInit"

    def get_interval(self):
        try:
            # 尝试获取频率属性
            freq = getattr(self.times, 'freq', None)
            if freq is not None:
                self.interval = freq
                if hasattr(self.interval, 'freqstr') and self.interval.freqstr == "H":
                    self.intervalhrs = self.interval.n
                else:
                    self.intervalhrs = getattr(self.interval, 'nanos', 3600000000000) / 1.0e9 / 3600.0
            else:
                # 如果没有freq属性，则计算时间间隔
                if len(self.times) > 1:
                    # 确保times是日期时间对象
                    if isinstance(self.times[0], (pd.Timestamp, dt)):
                        self.interval = self.times[1] - self.times[0]
                        self.intervalhrs = self.interval.total_seconds() / 3600.0
                    else:
                        # 默认为1小时
                        self.interval = pd.Timedelta(hours=1)
                        self.intervalhrs = 1.0
                else:
                    # 如果只有一个时间点，默认为1小时
                    self.interval = pd.Timedelta(hours=1)
                    self.intervalhrs = 1.0
        except (AttributeError, IndexError, TypeError) as e:
            # 处理任何异常情况
            logging.warning(f"计算时间间隔时出错: {e}，使用默认值1小时")
            self.interval = pd.Timedelta(hours=1)
            self.intervalhrs = 1.0
        return

    def __contains__(self, item):
        return item in self.times

    def __repr__(self):
        return repr(self.times)

    def __len__(self):
        return len(self.times)

    def __getitem__(self, i, circular=False):
        if i == -1 and not circular:
            return self.initialTime
        else:
            return self.strings[i]

    def last(self):
        return self.__getitem__(-1, circular=True)

    def __getslice__(self, i, j):
        return self.strings[i:j]

    def non_overlap(self):
        if self._int_overlap > 0:
            return TimeIndex(
                self.strings.index[: -1 - self._int_overlap + 1], self._str_start
            )
        else:
            return self
        return

    def post_horizon(self):
        if len(self) > self._int_division + 1:
            str_start = int(self.strings.loc[self._int_division + 1].strip("t"))
            return TimeIndex(self.strings.index[self._int_division + 1 :], str_start)
        else:
            return Series()
        return

    def last_non_overlap(self):
        return self.strings.index[-1 - self._int_overlap]

    def subdivide(self, division_hrs=24, overlap_hrs=0):
        # 确保intervalhrs不为零
        if self.intervalhrs == 0:
            logging.error("intervalhrs不能为零")
            # 创建一个空的TimeIndex并返回
            empty_index = TimeIndex(pd.DatetimeIndex([]), 0)
            # 返回一个包含空TimeIndex的列表
            return [empty_index]
            
        int_division = int(division_hrs / self.intervalhrs)
        int_overlap = int(overlap_hrs / self.intervalhrs)
        subsets = []
        
        # 如果没有足够的时间点进行划分，返回一个包含原始TimeIndex的列表
        if len(self) < int_division:
            logging.warning("时间点不足以进行划分，返回原始TimeIndex")
            return [self]
            
        for stg in range(int(len(self) / int_division)):
            start = stg * int_division
            end_point = start + int_division + int_overlap
            end_point = min(end_point, len(self))

            subset = TimeIndex(self.times[start:end_point], start)
            subset._int_overlap = int_overlap
            subset._int_division = int_division
            subsets.append(subset)

        if len(subsets[-1]) <= int_division:
            subsets[-1]._int_overlap = 0
        return subsets


def is_init(time):
    return getattr(time, "index", None) == "Init"
