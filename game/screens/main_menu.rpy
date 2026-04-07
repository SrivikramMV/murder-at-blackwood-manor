## Main Menu screen ############################################################
##
## Used to display the main menu when Ren'Py starts.
##
## https://www.renpy.org/doc/html/screen_special.html#main-menu

## This now uses your image as the main menu background
# Scale the image to cover the width of a 1920px screen, maintaining aspect ratio.
# The factor 1920.0 / 1688.0 is approximately 1.13744.
image main_menu_background = im.FactorScale("images/main.png", 1920.0 / 1688.0)

screen main_menu():
    tag menu

    # Add the background. If it's meant to be a fullscreen background,
    # simply adding it is often enough, or use xalign 0.5, yalign 0.5 for centering its anchor.
    # The previous xalign 10 was unusual; 0.5 would center.
    add "main_menu_background" # Or: add "main_menu_background" xalign 0.5 yalign 0.5

    # Use an hbox for horizontal layout of buttons
    hbox:
        # Position the hbox itself.
        # xalign 0.5 will center the hbox horizontally on the screen.
        xalign 0.5
        # yalign positions the top of the hbox. 0.95 places it near the bottom.
        # Adjust this value (e.g., 0.90, 0.98) to move it up or down slightly.
        yalign 0.95

        # Spacing applies horizontally between the buttons in an hbox.
        spacing 30 # Adjust as needed for the visual gap between buttons

        # Add the textbuttons directly into the hbox
        textbutton _("Start") action Start()

        textbutton _("Load") action ShowMenu("load")

        textbutton _("Preferences") action ShowMenu("preferences")

        textbutton _("About") action ShowMenu("about")

        if renpy.variant("pc") or (renpy.variant("web") and not renpy.variant("mobile")):
            ## Help isn't necessary or relevant to mobile devices.
            textbutton _("Help") action ShowMenu("help")

        if renpy.variant("pc"):
            ## The quit button is banned on iOS and unnecessary on Android and
            ## Web.
            textbutton _("Quit") action Quit(confirm=not main_menu)