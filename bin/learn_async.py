import asyncio
import random


async def some_coro(i):
    w = random.randint(1, 3)
    await asyncio.sleep(w)
    print(i, w)


async def main():
    background_tasks = set()

    for i in range(10):
        task = asyncio.create_task(some_coro(i))

        # Add task to the set. This creates a strong reference.
        background_tasks.add(task)

        # To prevent keeping references to finished tasks forever,
        # make each task remove its own reference from the set after
        # completion:
        task.add_done_callback(background_tasks.discard)

    while len(background_tasks) > 0:
        task = background_tasks.pop()
        await task

asyncio.run(main())
print('Done')
