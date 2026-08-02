from contextlib import contextmanager


@contextmanager
def transaction(pool):
    with pool.connection() as connection:
        with connection.transaction():
            yield connection
