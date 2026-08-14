// ======================================================================
// \title  Main.cpp
// \brief main program for the F' application. Intended for CLI-based systems (Linux, macOS)
//
// ======================================================================
// Used to access topology functions
#include <FprimeSoakTestReference/FprimeSoakTestReferenceDeployment/Top/FprimeSoakTestReferenceDeploymentTopology.hpp>
// OSAL initialization
#include <Os/Os.hpp>
// Used for signal handling shutdown
#include <signal.h>
// Used for command line argument processing
#include <getopt.h>
// Used for logging to the console
#include <Fw/Logger/Logger.hpp>

/**
 * \brief print command line help message
 *
 * This will print a command line help message including the available command line arguments.
 *
 * @param app: name of application
 */
void print_usage(const char* app) {
    Fw::Logger::log("Usage: ./%s [options]\n-h\tHelp\n", app);
}

/**
 * \brief shutdown topology cycling on signal
 *
 * The reference topology allows for a simulated cycling of the rate groups. This simulated cycling needs to be stopped
 * in order for the program to shutdown. This is done via handling signals such that it is performed via Ctrl-C
 *
 * @param signum
 */
static void signalHandler(int signum) {
    FprimeSoakTestReference::stopRateGroups();
}

/**
 * \brief execute the program
 *
 * Communications use the RFM69 radio (Rfm69Manager) exclusively; no TCP
 * hostname/port arguments are required.
 *
 * @param argc: argument count supplied to program
 * @param argv: argument values supplied to program
 * @return: 0 on success, something else on failure
 */
int main(int argc, char* argv[]) {
    I32 option = 0;

    Os::init();

    // Loop while reading the getopt supplied options
    while ((option = getopt(argc, argv, "h")) != -1) {
        switch (option) {
            case 'h':
                print_usage(argv[0]);
                return 0;
            case '?':
            default:
                print_usage(argv[0]);
                return 1;
        }
    }
    // Object for communicating state to the topology
    FprimeSoakTestReference::TopologyState inputs;
    inputs.mpu.device = "/dev/i2c-1";
    inputs.bmp.device.device = 0; // SPI bus 0
    inputs.bmp.device.select = 0; // SPI chip select 0 (RFM69 uses CS1)
    // PR #17 Rfm69 subtopology reads SPI/GPIO from topology state (defaults
    // match this Pi wiring: SPI0/CE1, RST on BCM GPIO26).
    inputs.rfm69.device.device = 0;
    inputs.rfm69.device.select = 1;
    inputs.rfm69.device.resetGpioChip = "/dev/gpiochip0";
    inputs.rfm69.device.resetGpioPin = 26;

    // Setup program shutdown via Ctrl-C
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    Fw::Logger::log("Hit Ctrl-C to quit\n");

    // Setup, cycle, and teardown topology
    FprimeSoakTestReference::setupTopology(inputs);
    FprimeSoakTestReference::startRateGroups(Fw::TimeInterval(0, 1000));  // Program loop cycling rate groups at 1KHz
    FprimeSoakTestReference::teardownTopology(inputs);
    Fw::Logger::log("Exiting...\n");
    return 0;
}
