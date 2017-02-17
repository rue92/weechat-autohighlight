try:
    import weechat
except Exception:
    print 'This script must be run under Weechat.'
    print 'Get WeeChat now at: http://www.weechat.org/'
    import_ok = False

import re

SCRIPT_NAME    = 'autohighlight'
SCRIPT_AUTHOR  = 'rue92'
SCRIPT_VERSION = '0.1.0'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Allows per buffer highlighting of recent messages by a user who has previously triggered highlighting.'

# TODO: Allow this to be user configurable.
HIGHLIGHT_NEXT_N_MESSAGES = 10
recent_highlights_by_buffer = {}

def resetRemainingMessages(buffer, nicktag):
    """Reset the highlighting for the nick under this buffer as if the nick had never been highlighted."""
    buffer_name = weechat.buffer_get_string(buffer, "name")
    highlights_for_buffer = recent_highlights_by_buffer.get(buffer_name, {})
    del highlights_for_buffer[nicktag]
    recent_highlights_by_buffer[buffer_name] = highlights_for_buffer

def refreshRemainingMessages(buffer, nicktag):
    """Refresh the highlighting for the nick under this buffer so that it receives an additional 10 messages worth of highlighting."""
    buffer_name = weechat.buffer_get_string(buffer, "name")
    highlights_for_buffer = recent_highlights_by_buffer.get(buffer_name, {})
    highlights_for_buffer[nicktag] = HIGHLIGHT_NEXT_N_MESSAGES - 1
    recent_highlights_by_buffer[buffer_name] = highlights_for_buffer

def decrementRemainingMessages(buffer, nicktag):
    """Decrement the highlighting for the nick under this buffer by one, unless the nick has not yet been highlighted in which case it initializes it to 10."""
    buffer_name = weechat.buffer_get_string(buffer, "name")
    highlights_for_buffer = recent_highlights_by_buffer.get(buffer_name, {})
    remaining_messages = highlights_for_buffer.get(nicktag, HIGHLIGHT_NEXT_N_MESSAGES)
    remaining_messages -= 1
    highlights_for_buffer[nicktag] = remaining_messages
    recent_highlights_by_buffer[buffer_name] = highlights_for_buffer
    return remaining_messages

def retrieveRemainingMessages(buffer, nicktag):
    """Retrieve the remaining number of messages that should be highlighted for the nick under this buffer."""
    buffer_name = weechat.buffer_get_string(buffer, "name")
    highlights_for_buffer = recent_highlights_by_buffer.get(buffer_name, {})
    remaining_messages = highlights_for_buffer.get(nicktag, 0)
    return remaining_messages

def newHighlight(buffer, nicktag):
    """Determine whether the nick under this buffer is not already been flagged to be highlighted for recency."""
    remaining_messages = retrieveRemainingMessages(buffer, nicktag)
    tags = weechat.buffer_get_string(buffer, "highlight_tags")
    if remaining_messages == 0 and nicktag not in tags:
        return True
    else:
        return False

def highlightTimedOut(buffer, nicktag):
    """Determine whether the nick under this buffer has timed out."""
    remaining_messages = retrieveRemainingMessages(buffer, nicktag)
    if remaining_messages == 0:
        return True
    else:
        return False

def shouldRefresh(message):
    """Determine whether the recency should be refreshed by checking to see if it was highlighted by the pre-existing highlight configuration."""
    words_option = weechat.config_get('weechat.look.highlight')
    highlight_words = weechat.config_string(words_option)
    regex_option = weechat.config_get('weechat.look.highlight_regex')
    highlight_regex = weechat.config_string(regex_option)
    regexes = [x.strip() for x in highlight_regex.split(',')]
    regex_match = False
    for regex in regexes:
        if weechat.string_has_highlight_regex(message, regex):
            regex_match = True
            break
        
    return (weechat.string_has_highlight(message, highlight_words) or
            regex_match)

def on_print_callback(data, buffer, date, tags, displayed, highlight, prefix, message):
    """Hook the messages printed to weechat and uses the given buffer, tags, highlight status, and message to highlight the next few messages sent by the highlighted nick."""
    if int(highlight):
        m = re.search(",(?P<nickname>nick_\S+?),", tags)
        if not m:
            return weechat.WEECHAT_RC_OK
        
        nicktag = m.group('nickname')
        if nicktag and newHighlight(buffer, nicktag):
            # Add nick tag to highlight_tags
            current_highlight_tags = weechat.buffer_get_string(buffer, "highlight_tags")
            if not current_highlight_tags:
                new_tags = nicktag
            else:
                new_tags = "{},{}".format(current_highlight_tags, nicktag)
            weechat.buffer_set(buffer, "highlight_tags", new_tags)
            decrementRemainingMessages(buffer, nicktag)
        elif shouldRefresh(message):
            refreshRemainingMessages(buffer, nicktag)
        elif highlightTimedOut(buffer, nicktag):
            highlight_tags = weechat.buffer_get_string(buffer, "highlight_tags")
            new_tags = re.sub(nicktag, '', highlight_tags)
            # This may or may not be super bad if tags are allowed to have commas
            new_tags = re.sub(",,", ",", new_tags)
            weechat.buffer_set(buffer, "highlight_tags", new_tags)
            resetRemainingMessages(buffer, nicktag)
        else:
            decrementRemainingMessages(buffer, nicktag)
                
    return weechat.WEECHAT_RC_OK
    

def main():
    hook = weechat.hook_print("", "", "", 1, "on_print_callback", "")
    

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
    main()
