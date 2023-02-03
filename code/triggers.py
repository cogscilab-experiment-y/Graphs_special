import os
import time
from datetime import datetime
from typing import List, Dict

# import parallel


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class _LoggingLevels(object):
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


class TriggerHandler(object):
    """
    Class that handles communication with Biosemi tigger interface.
    Usage:

    1. Create enumerator class for each trigger type e.g.
    class TriggerTypes(object):
        MATRIX = 'matrix'
        TRIAL = 'trial'
        TIME_PRESSURE = 'time_pressure'
        ANSWER = 'answer'

        @classmethod
        def vals(cls):
            return [value for name, value in vars(cls).items() if name.isupper()]

    2. Create instance of an object, preferably global
    TRIGGERS = TriggerHandler(TriggerTypes.vals(), trigger_params=['corr', 'key'])

    3. Connect with EEG (or no, depends on procedure mode)
    TRIGGERS.connect_to_eeg()

    4. Start each trial with marker
    TRIGGERS.set_curr_trial_start()

    5. Sent as many triggers as you want
    TRIGGERS.send_trigger(TriggerTypes.Trial)
    or
    win.callOnFlip(TRIGGERS.send_trigger, TriggerTypes.MATRIX)
    WARNING: If sent with win.CallOnFlip it's worth considering sending without delay,
    win.callOnFlip(TRIGGERS.send_trigger, TriggerTypes.MATRIX, with_delay=False)
    ...
    TRIGGERS.send_clear()

    6. Add extra info to all triggers in a current trial
    TRIGGERS.add_info_to_last_trigger(dict(corr=corr, key=key[0]), how_many=-1)

    7. Save results to .csv file
    TRIGGERS.save_to_file('triggers.csv')

    """

    def __init__(self, trigger_types: List[str], dummy_mode: bool = True, trigger_time: float = 0.004,
                 trigger_params: List[str] = None) -> None:
        """
        Args:
            trigger_types: List of possible trigger types.
            dummy_mode:  Use EEG or just behave alike.
            trigger_time: Time for delay between start and stop of sending a trigger.
            trigger_params: Additional trigger info to record, like correctness ect.
        """
        self._log: List[str] = list()
        self._creation_time = datetime.now()
        self._logger(f"TriggerHandler constructed with params: dummy_mode={dummy_mode},trigger_time={trigger_time}")
        self.trigger_types = trigger_types
        self._logger(f"Possible triggerTypes registered: {self.trigger_types}")
        self.dummy_mode = dummy_mode
        self._logger(f"Dummy mode: {self.dummy_mode}")
        if not dummy_mode:
            self.PORT = parallel.Parallel()
            self._logger("Connected to EEG (in constructor)")
        else:
            self.PORT = None
        self.trigger_time = trigger_time
        self._logger(f"Trigger time: {trigger_time}")
        self.trigger_params = ['trigger_no', 'trigger_type']
        if trigger_params is None:
            msg = 'No trigger info columns set, so only trigger_type will be recorded.'
            self._logger(msg, level=_LoggingLevels.WARNING)
            print(bcolors.WARNING + msg + bcolors.ENDC)
        else:
            self.trigger_params.extend(trigger_params)
        self._logger(f"Params registered: {self.trigger_params}")
        self._triggers = list()
        self._clear_trigger = 0x00
        self._trigger_counter: int = 1
        self._marker_pos: int = -1
        self._trigger_limit: int = 60
        self._logger(f"Trigger limit set to: {self._trigger_limit}")

    def _logger(self, msg: str, level: str = _LoggingLevels.INFO) -> None:
        """
        All triggers-related events are recorded and saved as a log.
        Args:
            msg: Event description.
            level: How important an event was.

        Returns:
            Nothing.
        """
        event_time = datetime.now() - self._creation_time
        self._log.append(f"# {str(event_time).ljust(15)} | {level.ljust(8)} | {msg}" + os.linesep)

    def connect_to_eeg(self):
        """
        TriggerHandler object may be created globally, but information about eeg usage is typically stored
        in a config file loading in a main body function.
        Returns:

        """
        if self.PORT is None:
            self.dummy_mode = False
            self.PORT = parallel.Parallel()
            self._logger("Connected to EEG (in connect_to_eeg())")
        else:
            self._logger("Connect to EEG already established.", level=_LoggingLevels.WARNING)
            print(bcolors.WARNING + "Already connected to EEG" + bcolors.ENDC)

    def send_trigger(self, trigger_type: str, info: Dict[(str, str)] = None, with_delay: bool = True) -> None:
        """
        Record trigger to send, and save info.
        Args:
            with_delay:
            trigger_type: Type of trigger for an allowed list.
            info: Additional info, also from a list of allowed params.

        Returns:
            Nothing.
        """
        if not self.dummy_mode:  # Trigger was sent, no delay.
            self.PORT.setData(self._trigger_counter)
            self._logger(f"Value: {self._trigger_counter} sent to EEG.")
        # Logging and params checking
        self._logger(
            f"send_trigger() run with params trigger_type={trigger_type}, info={info}, with_delay={with_delay}")
        if trigger_type not in self.trigger_types:
            self._logger(f"There's no trigger type called: {trigger_type}.", level=_LoggingLevels.CRITICAL)
            raise AttributeError(f"There's no trigger type called: {trigger_type}.")
        # Triggers may be sent in time critical moments, so clear_trigger will be sent manually
        if with_delay:
            time.sleep(self.trigger_time)
        if not self.dummy_mode and with_delay:
            self.PORT.setData(self._clear_trigger)
            self._logger('Clear message sent to EEG.')
        curr_trigger = dict(trigger_no=self._trigger_counter, trigger_type=trigger_type)
        if info is not None:  # some extra trigger info
            unregistered_params: List[str] = list(set(info) - set(self.trigger_params))
            if unregistered_params:
                msg = f"Params: {unregistered_params} are unregistered and won't be saved."
                self._logger(msg, level=_LoggingLevels.WARNING)
                print(bcolors.WARNING + msg + bcolors.ENDC)
            curr_trigger = {**curr_trigger, **info}
        self._trigger_counter += 1
        if self._trigger_counter > self._trigger_limit:
            self._trigger_counter = 1
        self._triggers.append(curr_trigger)
        if self._marker_pos >= 0:  # marker is recorded so position should be counted
            self._marker_pos += 1

    def send_clear(self) -> None:
        """
        Send end_of_signal message co EEG.
        Returns:
            Nothing.
        """
        if not self.dummy_mode:
            self.PORT.setData(self._clear_trigger)
            self._logger('Clear send to EEG (manually by user).')

    def set_curr_trial_start(self) -> None:
        """
            Start recording a new trial.
        Returns:
            Nothing.
        """
        if self._marker_pos != -1:
            msg = "New trial position marker was set without the previous ones being used."
            self._logger(msg, level=_LoggingLevels.WARNING)
            print(bcolors.WARNING + msg + bcolors.ENDC)
        self._marker_pos = 0

    def add_info_to_last_trigger(self, info: Dict[(str, str)], how_many: int = 1) -> None:
        """
        Some trigger info can't be added when trigger is sent, that's why it's possible to add info post factum.
        Args:
            info: Info to add to the last trigger, like correctness.
            how_many: How many of last triggers must be populated, if -1, add until last marker.

        Returns:
            Nothing.
        """
        if how_many < -1:
            msg = f"During add_info_to_last_trigger func how_many was set to {how_many} which doesn't have a sense."
            self._logger(msg, level=_LoggingLevels.CRITICAL)
            raise AttributeError(msg)
        if how_many == -1 and self._marker_pos == -1:
            msg = f"Cannot add info to curr trial cause no trial was started."
            self._logger(msg, level=_LoggingLevels.CRITICAL)
            raise AttributeError("No marker set.")
        if how_many == -1:  # add until a last marker position
            how_many = self._marker_pos
            self._marker_pos = -1
        if len(self._triggers) < how_many:
            self._logger("There's no prev trigger to add info to.", level=_LoggingLevels.CRITICAL)
            raise AttributeError("There's no prev trigger to add info to.")
        # Check if unregistered parameters are added
        unregistered_params: List[str] = list(set(info) - set(self.trigger_params))
        if unregistered_params:
            msg = f"Params: {unregistered_params} are unregistered so won't be saved."
            self._logger(msg, level=_LoggingLevels.WARNING)
            print(bcolors.WARNING + msg + bcolors.ENDC)
        for x in range(how_many):  # add info to prev triggers.
            intersecton = {key: info[key] for key in info if key in self._triggers[-1 - x]}
            if intersecton:  # check if some parameter will be overwritten
                msg = f"{intersecton.keys()} will be overwritten."
                self._logger(msg, level=_LoggingLevels.CRITICAL)
                print(bcolors.FAIL + msg + bcolors.ENDC)
            self._triggers[-1 - x] = {**self._triggers[-1 - x], **info}

    def _prepare_printable_form(self) -> List[str]:
        """
        Make a printable form from a list of triggers.
        Returns:
            List of human-readable strings.
        """
        res = list()
        res.append(f"{','.join(self.trigger_params)}")
        for trig in self._triggers:
            line: str = ''
            for key in self.trigger_params:
                line += f"{trig.get(key, 'UNKNOWN')},"
            if self.trigger_params:  # remove last underscore
                line = line[:-1]
            res.append(line)
        return res

    def print_trigger_list(self) -> None:
        """
        Print triggers to screen.
        Returns:
            Nothing.
        """
        for line in self._prepare_printable_form():
            print(line)

    def save_to_file(self, file_name: str) -> None:
        """
        Save trigger info to file.
        Args:
            file_name:

        Returns:
            Nothing.
        """
        with open(file_name, 'w') as beh_file:
            beh_file.writelines([x + os.linesep for x in self._prepare_printable_form()])
            beh_file.writelines(self._log)
