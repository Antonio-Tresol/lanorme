# why: negative - two argparse subcommand registrations; the flag names, help text and defaults are the specification of distinct commands, so the parallel add_argument calls are not clonable.
def register_build_command(parser):
    parser.add_argument("--target", help="build target name")
    parser.add_argument("--release", action="store_true", help="optimise the build")
    parser.add_argument("--jobs", type=int, default=4, help="parallel jobs")
    parser.add_argument("--out", default="dist", help="output directory")
    parser.set_defaults(handler=run_build)
    return parser


def register_deploy_command(parser):
    parser.add_argument("--environment", help="deploy environment")
    parser.add_argument("--dry-run", action="store_true", help="do not apply changes")
    parser.add_argument("--replicas", type=int, default=2, help="replica count")
    parser.add_argument("--region", default="eu-west-1", help="cloud region")
    parser.set_defaults(handler=run_deploy)
    return parser
