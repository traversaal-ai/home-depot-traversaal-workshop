import asyncio
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
import os
import warnings
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
from google.adk.agents import LlmAgent
from google.adk.tools.function_tool import FunctionTool
import uuid
from google.adk.tools import FunctionTool
import re
from google.cloud import dlp_v2
from google import genai
from google.genai.types import SafetySetting, HarmCategory, HarmBlockThreshold

safety_settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    ),
]

info_types = [
    {"name": "EMAIL_ADDRESS"},
    {"name": "PHONE_NUMBER"},
    {"name": "CREDIT_CARD_NUMBER"},
    {"name": "US_SOCIAL_SECURITY_NUMBER"},
    {"name": "PERSON_NAME"},
    {"name": "IP_ADDRESS"},
    {"name": "DATE_OF_BIRTH"},
    {"name": "STREET_ADDRESS"},
    {"name": "PASSWORD"},
    {"name": "URL"},
    {"name": "AGE"},
    {"name": "VEHICLE_IDENTIFICATION_NUMBER"},
    {"name": "IBAN_CODE"},
    {"name": "MAC_ADDRESS"},
    {"name": "US_EMPLOYER_IDENTIFICATION_NUMBER"},
    {"name": "LOCATION_COORDINATES"}
]

def mask_sensitive_data(project_id, text):
    # Initialize the client
    client = dlp_v2.DlpServiceClient()

    # Construct the parent resource name
    parent = f"projects/{project_id}"

    # Configure what we want to find
    inspect_config = {"info_types": info_types}

    # Construct the item to inspect
    item = {
        "byte_item": {
            "type": "TEXT_UTF8",
            "data": text.encode('utf-8')
        }
    }

    # Create the request object
    request = {
        "parent": parent,
        "inspect_config": inspect_config,
        "item": item
    }

    # Make the API call
    response = client.inspect_content(request=request)

    # Create masked version of text
    masked_text = text

    # Sort findings by position (in reverse order to avoid offsetting issues)
    findings = sorted(
        response.result.findings,
        key=lambda f: f.location.byte_range.start,
        reverse=True
    )

    # Replace each finding with asterisks
    for finding in findings:
        start = finding.location.byte_range.start
        end = finding.location.byte_range.end
        masked_text = masked_text[:start] + '*' * (end - start) + masked_text[end:]

    return masked_text


class SecurityBlocker:
    def __init__(self):
        # Comprehensive list of SQL injection patterns
        self.dangerous_patterns = [
            # Database Destruction Patterns
            r"DROP\s+DATABASE",
            r"DROP\s+SCHEMA\s+.*CASCADE",
            r"DROP\s+ALL\s+TABLES",
            r"DROP\s+TABLE\s+.*CASCADE",
            r"TRUNCATE\s+TABLE\s+.*CASCADE",
            r"ALTER\s+TABLE\s+.*DROP\s+COLUMN",
            r"DROP\s+INDEX",
            r"DROP\s+TRIGGER",
            r"DROP\s+FUNCTION",
            r"DROP\s+VIEW",
            r"DROP\s+SEQUENCE",
            r"DROP\s+USER",
            r"REVOKE\s+ALL\s+PRIVILEGES",
            r"ALTER\s+SYSTEM\s+SET",
            r"DROP\s+TABLESPACE",
            r"EXEC\s+sp_configure",
            r"EXEC\s+xp_cmdshell.*rm\s+-rf",
            r"EXEC\s+xp_cmdshell.*del",
            r"EXEC\s+sp_MSforeachtable",
            r"D/\*.*\*/ROP",
            r"DR/\*.*\*/OP",
            r"exec\s*\(\s*['\"]DROP",
            r"PREPARE\s+.*DROP",
            r"DROP\s+TABLE",

            # Basic Authentication Bypass
            r"'\s*OR\s*1=1\s*--",
            r"'\s*OR\s*'1'='1'",
            r"'\s*OR\s*'1'='1'\s*--",
            r"'\s*OR\s*'1'='1'\s*#",
            r"'\s*OR\s*'1'='1'\s*/\*",
            r"'\)\s*OR\s*'1'='1'\s*--",
            r"'\)\s*OR\s*\('1'='1'\s*--",
            r"'\s*OR\s*'1'='1'\s*LIMIT\s*1\s*--",
            r"'\s*OR\s*1=1",
            r"'\s*OR\s*1=1\s*--",
            r"'\s*OR\s*1=1\s*#",
            r"'\s*OR\s*1=1\s*/\*",
            r"'\)\s*OR\s*1=1\s*--",
            r"'\)\s*OR\s*\(1=1\s*--",
            r"'\s*OR\s*1=1\s*LIMIT\s*1\s*--",
            r"'=1\s*--",

            # Comment-Based
            r"--",
            r"#",
            r"/\*",
            r"\*/",
            r"';\s*--",
            r"';\s*#",
            r"';\s*/\*",
            r"'\);\s*--",
            r"'\)#",
            r"'\);\s*--",

            # UNION-Based
            r"UNION\s+SELECT.*FROM",
            r"UNION\s+SELECT\s+NULL",
            r"UNION\s+ALL\s+SELECT",
            r"UNION\s+SELECT\s+@@version",
            r"UNION\s+SELECT.*information_schema",

            # Blind SQL Injection
            r"'\s*AND\s*1=1",
            r"'\s*AND\s*IF",
            r"'\s*AND\s*SLEEP",
            r"'\s*AND\s*\(SELECT",
            r"SUBSTRING\s*\(\s*SELECT",

            # Time-Based
            r"WAITFOR\s+DELAY",
            r"SLEEP\s*\(",
            r"pg_sleep",
            r"DBMS_PIPE\.RECEIVE_MESSAGE",
            r"BENCHMARK\s*\(",

            # Database-Specific Commands
            r"SELECT\s+LOAD_FILE",
            r"INTO\s+OUTFILE",
            r"xp_cmdshell",
            r"master\.\.sysdatabases",
            r"UTL_INADDR",
            r"UTL_HTTP",
            r"DBMS_PIPE",

            # Stacked Queries
            r";\s*DROP\s+TABLE",
            r";\s*DELETE\s+FROM",
            r";\s*UPDATE\s+.*SET",
            r";\s*INSERT\s+INTO",
            r";\s*CREATE\s+TABLE",
            r";\s*TRUNCATE\s+TABLE",

            # Data Exfiltration
            r"GROUP_CONCAT",
            r"LOAD_FILE",
            r"INTO\s+OUTFILE",

            # Privilege Escalation
            r"GRANT\s+ALL\s+PRIVILEGES",
            r"super_priv",
            r"user_privileges",

            # NoSQL Injection
            r'\{\s*"?\$ne"\s*:',
            r'\{\s*"?\$gt"\s*:',
            r'\{\s*"?\$where"\s*:',

            # Information Gathering
            r"SELECT\s+@@version",
            r"SELECT\s+@@hostname",
            r"SELECT\s+@@datadir",
            r"SELECT\s+USER\(\)",
            r"SELECT\s+CURRENT_USER\(\)",
            r"SELECT\s+SYSTEM_USER\(\)"

            # XSS
            r"<\s*script",  # Changed from <script.*?>
            r"onload",      # Simplified
            r"rm",          # Simplified
            r"sudo",        # Simplified
            r"execute.*command",  # Modified pattern
            r"ignore.*instructions",  # Modified pattern
            r"harmful.*assistant",    # Modified pattern
            r"\*\*\*"

            r"sudo\s+.*",            # Match any sudo command
            r"rm\s+-[rf]+\s+.*",     # Match rm with force/recursive flags
            r"execute.*command",      # Match execute commands
            r";\s*rm\s+-[rf]+.*",    # Match rm after semicolon
            r";\s*wget\s+.*",        # Match wget after semicolon
            r";\s*curl\s+.*",        # Match curl after semicolon
            r";\s*nc\s+.*",          # Match netcat after semicolon
            r";\s*ping\s+-.*",       # Match ping with flags

            # Path Traversal
            r"\.\.\/+",              # Match directory traversal (forward slash)
            r"\.\.\\+",              # Match directory traversal (backslash)
            r"\/etc\/passwd",        # Match sensitive file access
            r"c:\\windows\\system32", # Match Windows system directory

            # DoS Attack Patterns
            r"ping.*-[ls]\s*65\d*",  # Match ping flood attempts
            r"fork.*bomb",           # Match fork bombs

            # Buffer Overflow
            r"A{1000,}",             # Match long sequences of 'A'
            r"%x{100,}",             # Match long sequences of %x
            r"%s{100,}",             # Match long sequences of %s

            # Log4j
            r"\$\{jndi:.*\}",        # Match JNDI lookups
            r"\$\{env:.*\}",         # Match environment lookups
            r"\$\{ctx:.*\}",         # Match context lookups

            # Network Attacks
            r"slowloris",            # Match slowloris attack
            r"synflood",             # Match SYN flood attack
            r"tcpkill",              # Match TCP kill attack

            # Combined Command Injection Patterns
            r"(sudo|rm|wget|curl|nc)\s+.*-[rflsp]+.*",  # Match command with dangerous flags
            r";\s*(sudo|rm|wget|curl|nc)\s+.*",         # Match commands after semicolon

            # Command Chaining
            r"&&\s*(rm|wget|curl)",  # Match command chaining with &&
            r"\|\|\s*(rm|wget|curl)", # Match command chaining with ||
            r"`.*(?:rm|wget|curl).*`", # Match backtick command execution

            # XSS Patterns (enhanced)
            r"<\s*script.*?>",       # Match script tags
            r"javascript:",          # Match javascript protocol
            r"on(?:load|click|mouseover|error|submit)=" # Match event handlers
        ]

        self.obfuscation_patterns = [
            # === Leetspeak/Number Substitutions ===
            # SELECT variations
            r"(?:s3l3ct|s3lect|sel3ct|5elect|se1ect|selec7)",
            r"(?:5el3ct|5e1ect|s31ect|s313ct)",

            # DROP variations
            r"(?:dr0p|dr0p|dr0p|dr0p|dr0p)",
            r"(?:dr0p|dr0p|dr0p|d7op|dr9p)",

            # UNION variations
            r"(?:un10n|uni0n|un1on|un!on|un!0n)",
            r"(?:un!0n|uni9n|un10n|un1on)",

            # Common test conditions
            r"(?:1=1|l=l|1=l|l=1)",
            r"(?:1='1'|1=true|1 is 1)",

            # Common auth bypass
            r"(?:adm1n|4dmin|@dmin|admin1|@dm1n)",
            r"(?:p@ssw0rd|p@55w0rd|passw0rd|pa55word)",

            # === Typo Variants ===
            r"(?:sleect|selct|selecct|slect|seelct)",  # SELECT misspellings
            r"(?:drp|dropp|dorp|dorpp|dop)",          # DROP misspellings
            r"(?:unoin|iunon|unnion|unioon|ubion)",   # UNION misspellings
            r"(?:wher|whre|wheer|wherr|wherre)",      # WHERE misspellings
            r"(?:udpate|updaet|updte|updatte)",       # UPDATE misspellings
            r"(?:isner|insret|insetr|insrt)",         # INSERT misspellings
            r"(?:delte|deleet|deleete|delet)",        # DELETE misspellings

            # === Obfuscation Techniques ===
            # URL and hex encoding
            r"%(?:[0-9A-Fa-f]{2})+",                 # URL encoded sequences
            r"(?:\\x[0-9A-Fa-f]{2})+",               # Hex encoded sequences

            # Embedded comments in keywords
            r"S(?:\s|\/\*.*?\*\/)*E(?:\s|\/\*.*?\*\/)*L(?:\s|\/\*.*?\*\/)*E(?:\s|\/\*.*?\*\/)*C(?:\s|\/\*.*?\*\/)*T",  # SELECT with comments
            r"U(?:\s|\/\*.*?\*\/)*N(?:\s|\/\*.*?\*\/)*I(?:\s|\/\*.*?\*\/)*O(?:\s|\/\*.*?\*\/)*N",  # UNION with comments
            r"D(?:\s|\/\*.*?\*\/)*R(?:\s|\/\*.*?\*\/)*O(?:\s|\/\*.*?\*\/)*P",  # DROP with comments

            # Character insertion
            r"s.{0,2}e.{0,2}l.{0,2}e.{0,2}c.{0,2}t", # Characters inserted between normal letters
            r"d.{0,2}r.{0,2}o.{0,2}p",               # Characters inserted in DROP
            r"u.{0,2}n.{0,2}i.{0,2}o.{0,2}n",        # Characters inserted in UNION

            # Double encoding
            r"%25[0-9A-Fa-f]{2}",                    # Double URL encoding

            # Unicode alternative characters
            r"(?:ｓｅｌｅｃｔ|ｄｒｏｐ|ｕｎｉｏｎ)",           # Fullwidth unicode
            r"(?:＜script＞)",                        # Fullwidth script tags

            # Mixed encoding techniques
            r"(?:%73%65%6c%65%63%74|%64%72%6f%70)",  # URL encoded SQL words

            # Case manipulation with other techniques
            r"(?:[Ss][Ee][Ll][Ee][Cc][Tt])",        # Mixed case SELECT
            r"(?:[Dd][Rr][Oo][Pp])",                # Mixed case DROP

            # Common evasion techniques
            r"(?:/*!50000select*/)",                 # MySQL version comment bypass
            r"(?:concat\(.{1,30}\))",                # Concatenation functions
            r"(?:char\([0-9,]+\))",                  # Character construction

            # Combined techniques
            r"(?:\bu%6eion\b)",                      # Partial encoding
            r"(?:\bd%72op\b)",                       # Partial encoding

            # Generic pattern for detection of mixed alphanumeric substitutions
            r"(?:[a-zA-Z0-9_%@$]{1,2}){3,}[=<>!]{1,2}(?:[a-zA-Z0-9_%@$]{1,2}){1,}",

            r"%53%45%4c%45%43%54",            # SELECT
            r"%44%52%4f%50",                  # DROP
            r"%55%4e%49%4f%4e",               # UNION
            r"%46%52%4f%4d",                  # FROM
            r"%57%48%45%52%45",               # WHERE
            r"%41%4e%44",                     # AND
            r"%4f%52",                        # OR
            r"%49%4e%53%45%52%54",            # INSERT
            r"%55%50%44%41%54%45",            # UPDATE
            r"%44%45%4c%45%54%45",            # DELETE
            r"%43%52%45%41%54%45",            # CREATE
            r"%41%4c%54%45%52",               # ALTER
            r"%54%52%55%4e%43%41%54%45",      # TRUNCATE
            r"%45%58%45%43",                  # EXEC

            # Also match lowercase hex variants
            r"%53%65%6c%65%63%74",            # SELECT (lowercase hex)
            r"%64%72%6f%70",                  # DROP (lowercase hex)

            # Match with whitespace or URL-encoded spaces
            r"%53%45%4c%45%43%54(?:\s|%20|\+)+.*?%46%52%4f%4d",  # SELECT...FROM
        ]

        # Combine all patterns
        self.all_patterns = self.dangerous_patterns + self.obfuscation_patterns

        # Compile patterns with case insensitivity and multiline support
        self.patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in self.all_patterns]

    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess query to handle common evasion techniques before pattern matching.

        Args:
            query (str): The original query

        Returns:
            str: Preprocessed query
        """
        processed = query

        # Decode URL encoded characters
        try:
            # Try to decode URL encoding
            import urllib.parse
            decoded = urllib.parse.unquote(processed)
            if decoded != processed:
                processed = decoded

                # Try second level decoding for double encoding
                second_decoded = urllib.parse.unquote(processed)
                if second_decoded != processed:
                    processed = second_decoded
        except:
            pass

        # Replace common character substitutions
        substitutions = {
            '0': 'o', '1': 'i', '1': 'l', '3': 'e', '4': 'a',
            '5': 's', '6': 'g', '7': 't', '8': 'b', '9': 'g',
            '@': 'a', '$': 's', '+': 't', '!': 'i'
        }

        # Create alternate version with substitutions for additional checking
        alt_processed = processed
        for char, replacement in substitutions.items():
            alt_processed = alt_processed.replace(char, replacement)

        # If the substituted version is different, also check against patterns
        if alt_processed != processed:
            return alt_processed

        return processed

    def evaluate_query(self, query: str) -> dict:
        """
        Evaluate a query and return detailed results.

        Args:
            query (str): The query to evaluate

        Returns:
            dict: Result containing status and matched patterns
        """

        preprocessed_query = self._preprocess_query(query)

        matches = []
        for pattern in self.patterns:
            if pattern.search(query):
                matches.append(pattern.pattern)

        result = {
            'status': 'BLOCKED' if matches else 'PASS',
            'matches': matches,
            'query': query,
            'preprocessed': preprocessed_query if preprocessed_query != query else None
        }

        return result

def evaluate_prompt(query: str) -> str:
    """Evaluate a prompt for harmful content with detailed feedback."""
    blocker = SecurityBlocker()
    result = blocker.evaluate_query(query)

    print(f"\033[1;91m\nQuery: {result['query']}\033[0m")
    print(f"\033[1;91mStatus: {result['status']}\033[0m")

    if result['matches']:
        print("\033[1;93mMatched patterns:\033[0m")
        for pattern in result['matches']:
            print(f"- {pattern}")

        print("\033[1;91m\n!!! MALICIOUS CONTENT DETECTED - TERMINATING EXECUTION !!!\033[0m")
        import os
        #os._exit(1)  # Immediately terminate the process when malicious content is detected -- DISABLE FOR EVALUATION

    return result['status']
