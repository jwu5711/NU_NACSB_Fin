from collections import defaultdict
from typing import Dict, Set, Tuple, List
import GS_Classes as gsc


def employee_without_match(matches: Dict[str, str], employees: Set[str]) -> str:
    """
    Helper function to determine if employee is unmatched.
    Returns the first employee encountered that is not
    yet matched. employees can be matched with a job, or
    themselves. If matched to themselves, this means that the
    matching algorithm has exhausted their entire preference
    list. If all employees are matched, this function will
    return None, and we will break from deferred acceptance algorithm.
    """
    for employee in employees:
        if employee not in matches:
            return employee


def da(
    employee_preferences: Dict[str, List[gsc.Route]], job_preferences: Dict[Tuple[gsc.Route, int], List[str]]
) -> Tuple[Dict[str, gsc.Route], Dict[str, gsc.Route]]:
    """
    Implementation of the deferred acceptance (DA) algorithm (also
    (also as Gale-Shapley algorithm), first published in 1962.
    Iterates through all employees and their preference lists,
    and tentatively assigns them to the most preferred job on
    their list, only re-assigning them if the job they are
    tentatively assigned to is "proposed to" by an employee
    that the job desires more. When this happens, the initial
    employee is bumped (because the job prefers its new offer),
    and then the algorithm iteratively attempts to assign this
    "bumped" employee a remaining job as high on their preference
    list as possible. Algorithm terminates when either (1) all
    employees have been assigned, or (2) all employees have
    exhausted their preference lists (no more jobs available).
    """
    job_queue: Dict = defaultdict(int)
    employees: List[str] = list(employee_preferences.keys())
    matches: Dict[str, gsc.Route] = {}

    job_info: Dict[str, Tuple[gsc.Route, int, List[str]]] = {
    route_obj.ID: (route_obj, capacity, prefs)
    for (route_obj, capacity), prefs in job_preferences.items()
    }

    job_assignments: Dict[gsc.Route, List[str]] = defaultdict(list)
    current_empl = None
    while True:
        # get the next available employee that is still unmatched to a job
        employee = employee_without_match(matches, employees)
        # once all employees have been matched (to a job or themselves), employee_without_match function will return
        # a None type object, and we will break from while loop. If an employee is matched to themself it means the
        # algorithm exhausted their preference list (e-Resume), and was not able to match them with any job
        if not employee:
            break

        # queue (counter) to track which job we are currently considering for the current employee
        # i.e., if job_index is 2, then we are considering the 3rd job on the given
        # employee's preference list (0-indexing)
        job_index = job_queue[employee]
        # increment counter so that next time through loop, we consider the next job on the preference list
        # since this is a defaultdict, new entries automatically start at 0
        job_queue[employee] += 1

        # Try to match the current employee with the next available job on their rank ordered list, if available
        if job_index < len(employee_preferences[employee]):
            job = employee_preferences[employee][job_index]
            # print(employee, job.ID)
        # if we've gone through the employee's entire list, assign employee to themself to indicate unmatched
        else:
            matches[employee] = employee
            continue
        
        route_id = job.ID
        if route_id not in job_info:
            continue

        route_obj, capacity, prefs = job_info[route_id]
        assigned = job_assignments[route_obj]

        # If job has available capacity, assign directly
        if len(assigned) < capacity:
            assigned.append(employee)
            matches[employee] = route_obj
            current_empl = employee
        else:
            # Check if this employee is preferred over any current match, 
            # should never be true, see NU midterm or final report
            worse_candidate = None
            for assigned_emp in assigned:
                if (
                    employee in prefs and assigned_emp in prefs
                    and prefs.index(employee) < prefs.index(assigned_emp)
                ):
                    worse_candidate = assigned_emp
                    break

            if worse_candidate:
                assigned.remove(worse_candidate)
                assigned.append(employee)
                current_empl = employee
                matches[employee] = route_obj
                del matches[worse_candidate]
    # return two-sided match (employee to job and job to employee), and one-sided match (employee to job)
    return matches, {employee: matches[employee] for employee in employees}, current_empl
