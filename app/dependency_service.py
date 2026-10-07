from app.repository import get_dependencies


def would_create_cycle(
    task_id: str,
    dependency_id: str,
) -> bool:
    """
    Check whether making task_id depend on dependency_id
    would create a circular dependency.
    """

    visited: set[str] = set()

    def dfs(current_task_id: str) -> bool:

        # We reached the task we are trying to create a dependency from.
        if current_task_id == task_id:
            return True

        if current_task_id in visited:
            return False

        visited.add(current_task_id)

        dependencies = get_dependencies(current_task_id)

        for dependency in dependencies:
            if dfs(dependency):
                return True

        return False

    return dfs(dependency_id)