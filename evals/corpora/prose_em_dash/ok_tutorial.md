# Getting Started with the Toolkit

This tutorial walks you through your first project from an empty folder to a working build. It assumes you have the toolkit installed already. If you do not, follow the installation guide first and then return here. The whole process should take about fifteen minutes.

Begin by creating a new directory for your work. Open a terminal, make the folder, and move into it. Run the init command, which sets up the basic structure and a sample configuration file. You will see a short summary of what was created. Take a moment to read it, since it explains where each piece lives.

Next, open the configuration file in your editor. The defaults are sensible, so you only need to change a few values. Set the project name and the output directory to suit your taste. Save the file and return to the terminal. The tool watches this file and reloads whenever it changes, so you rarely need to restart.

Now add your first source file. Create a file in the source folder and write a few lines following the example in the documentation. Keep it simple for this first pass. Run the build command and watch the output appear in the directory you configured. A green message confirms that everything worked.

If something goes wrong, the error messages are designed to help. Each one names the file and line where the trouble lies and suggests a likely fix. Read it carefully before searching elsewhere, because the answer is usually right there. Most early problems come from a small typo in the configuration file rather than anything deeper.

With a working build in hand, you are ready to explore further. The reference guide covers every option in detail, and the examples folder shows complete projects you can study. Experiment freely, since the tool never touches files outside your project. When you are comfortable here, the advanced guide will take you the rest of the way.
