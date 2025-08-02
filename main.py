#!/usr/bin/env python

import argparse
import io
import multiprocessing as mp
import os
import random
import sys
import time
import traceback

from ocean import Ocean


class SimText:
    @staticmethod
    def paint(ocean: Ocean, file=sys.stdout):
        print("\033[0;0H\n", file=file)
        print(ocean, file=file)

    @staticmethod
    def random_ocean(width: int, height: int) -> Ocean:
        x, y, r, offset = 0, 0, random.Random(), 78887
        ocean = Ocean(width, height)

        for _ in range(width):
            x = (x + offset) % width
            if x & 8 == 0:
                for _ in range(height):
                    y = (y + offset) % height
                    if y & 8 == 0:
                        rand = r.random()
                        if rand < 0.6:
                            ocean.add_fish(x, y)
                        elif rand >= 0.9:
                            ocean.add_shark(x, y)

        return ocean


def simulate_ocean(
    ocean: Ocean,
    starve_time: int,
    frames: int,
    kill_repeat: bool,
    queue: mp.Queue,
    sigInt: mp.Event,
) -> None:
    """
    Simulate the ocean
    """
    # top & bottom
    top_bot = "\n     " + "!" * (2 * ocean.width - 8)

    def mid(word: str) -> str:
        s1 = s2 = (2 * ocean.width - 16 - len(word)) // 2
        s2 += len(word) % 2
        return "\n     !!!!" + " " * s1 + word.upper() + " " * s2 + "!!!!"

    def dead_str() -> str:
        return top_bot + mid("dead") + top_bot + "\n"

    def exc_str() -> str:
        return f"{top_bot}{mid('exception')}{top_bot}\n"

    def halt_str() -> str:
        return f"{top_bot}{mid('halted')}{top_bot}\n"

    def kill_str() -> str:
        return f"{top_bot}{mid('killed')}{top_bot}\n"

    def repeat_str(x: int) -> str:
        msg = f"repeat (frame: {x})"
        return f"{top_bot}{mid(msg)}{top_bot}\n"

    # hash set
    # seen = {hash(ocean)}
    seen = {hash(ocean): [0]}

    # track if we're going to run a limited number of frames
    counter = 0

    def forever():
        """
        simple generator that tells the loop to keep going or to halt
        """
        nonlocal counter
        counter += 1
        if frames > 0:
            if counter == frames:
                return
        yield True

    try:
        while next(forever()):
            # print(
            #     f"\033[50;0H {counter} frames calculated",
            #     end="",
            #     file=sys.stdout,
            # )
            # counter += 1
            queue.put((ocean, ""))

            ocean = ocean.time_step(starve_time)
            # check for exit conditions
            if ocean.is_dead:
                queue.put((ocean, dead_str()))
                break
            if sigInt.is_set():
                queue.put((ocean, kill_str()))
                break
            if kill_repeat:
                if (h := hash(ocean)) in seen:
                    queue.put((ocean, repeat_str(seen[h][0])))
                    break
                else:
                    seen.setdefault(h, []).append(counter)
    except KeyboardInterrupt:
        queue.put((ocean, kill_str()))
    except:
        # record the exception into a buffer
        exc_buffer = io.StringIO()
        traceback.print_exc(file=exc_buffer)
        # return the halted ocean with the exc/tb
        queue.put((ocean, exc_str() + "\n" + exc_buffer.getvalue()))
    else:
        # natural exit
        # queue.put((ocean, halt_str()))
        queue.put((None, None))
        # signal to consumers that we are done
        queue.close()
        sigInt.clear()


def run_ocean(
    ocean: Ocean,
    sigInt: mp.Event,
    *,
    starve_time: int = 3,
    fps: int = 24,
    frames: int = -1,
    kill_repeat: bool = False,
) -> tuple[mp.Process, mp.Queue]:
    """
    Runs the ocean in a separate process
    """
    queue = mp.Queue(maxsize=int(fps * 1.5))
    # queue = mp.Queue()
    # signal = threading.Event()
    # signal.set()

    # runner = threading.Thread(target=simulate_ocean, args=(ocean, starve_time, frames, queue, sigInt,))
    runner = mp.Process(
        target=simulate_ocean,
        args=(
            ocean,
            starve_time,
            frames,
            kill_repeat,
            queue,
            sigInt,
        ),
    )
    runner.daemon = True
    # runner.setDaemon(True)  # for threading
    runner.start()

    # return the running process and the event queue
    return runner, queue


def args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("SimText command line arguments")

    parser.add_argument(
        "-x",
        "--width",
        default=40,
        type=int,
        metavar="WIDTH",
        help="The width of the ocean",
    )
    parser.add_argument(
        "-y",
        "--height",
        default=40,
        type=int,
        metavar="HEIGHT",
        help="The height of the ocean",
    )
    parser.add_argument(
        "-s",
        "--starve_time",
        default=3,
        type=int,
        metavar="STARVE_TIME",
        help="The starve time for the sharks",
    )
    parser.add_argument(
        "-f",
        "--fps",
        default=24,
        type=int,
        metavar="FPS",
        help="Frames per second to run the simulation at",
    )
    parser.add_argument(
        "-r",
        "--frames",
        default=-1,
        type=int,
        metavar="FRAMES",
        help="The max number of frames to run",
    )
    parser.add_argument(
        "-k",
        "--kill-repeat",
        action="store_true",
        help="Flag determines if we should kill the ocean on a repetition",
    )

    return parser


def main(sigInt: mp.Event) -> None:
    # parse our CLI arguments
    kwargs = vars(args_parser().parse_args())

    width, height = kwargs.pop("width"), kwargs.pop("height")
    fps, starve_time = kwargs["fps"], kwargs["starve_time"]

    # initialize a random ocean
    ocean = SimText.random_ocean(width, height)
    SimText.paint(ocean)

    # start the ocean simulation thread
    proc, queue = run_ocean(ocean, sigInt, **kwargs)

    # frame count
    frame = -1

    # sleep factor fudges the sleep duration to account for overhead
    sleep_factor = 1.0 + (2.0 / 30.0)
    # sleep_factor = 1.06775
    # sleep_factor = 1.0

    # sleep duration - fudged to account for overhead
    sleep = 1.0 / (fps**sleep_factor)

    input("press enter to start: ")

    # track our start time
    start = time.time()

    # play the ocean
    while proc.is_alive() or not queue.empty():
        try:
            ocean, msg = queue.get()
            if ocean is None:
                break

            # increment frame
            frame += 1

            # print the ocean
            print("\033[0;0H\n")
            print(str(ocean) + msg)

            # print current frame info
            elapsed = time.time() - start
            print(
                "[",
                f"{elapsed:.1f}s",
                "]",
                "frame:",
                frame,
                "(",
                f"x:{width}",
                f"y:{height}",
                f"s:{starve_time}",
                f"f:{fps}",
                ")",
                "fps:",
                f"{frame / elapsed:.1f}",
                "[",
                hash(ocean),
                "]",
                end="",
            )

            # sleep for a bit
            time.sleep(sleep)
        except KeyboardInterrupt:
            sigInt.set()
            raise


if __name__ == "__main__":
    interrupt = False
    # process signal
    sigInt = mp.Event()

    try:
        # main(sigInt, *sys.argv[1:])
        main(sigInt)
        print()
    except KeyboardInterrupt:
        interrupt = True
        sigInt.wait()  # wait for the signal to be cleared
        sys.stdout.flush()
        print()
        # raise
    except:  # pylint: disable=bare-except
        # os.system('clear')
        raise
    finally:
        if interrupt:
            input("\n^C: press enter to clear: ")
            os.system("clear")
